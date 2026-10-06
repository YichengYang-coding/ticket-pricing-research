"""Point-in-time historical ticket-price research; not an execution/PnL backtest."""
from pathlib import Path
import hashlib, json, sys
import numpy as np
import pandas as pd
from scipy.linalg import lstsq
from scipy.stats import t as student_t
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
TZ='America/New_York'
FIRST=pd.Timestamp('2026-07-01 20:00',tz=TZ)
LAST=pd.Timestamp('2026-09-27 20:00',tz=TZ)
OOS=pd.Timestamp('2026-08-01 20:00',tz=TZ)
TD=pd.Timedelta

def save(f,name):f.to_csv(ROOT/'processed'/name,index=False,encoding='utf-8-sig')
def spline(d):
    z=np.log1p(np.asarray(d,dtype=float))
    return np.column_stack([z]+[np.maximum(z-np.log1p(k),0) for k in [7,14,30,60]])

def load():
    f=pd.read_csv(ROOT/'processed/research_accepted_records.csv',low_memory=False,
        dtype={'section':str,'row':str,'source':str,'qty_group':str})
    for c in ['observed_at_edt','event_start_local']:f[c]=pd.to_datetime(f[c],utc=True).dt.tz_convert(TZ)
    f['observed_day']=f.observed_at_edt.dt.strftime('%Y-%m-%d')
    return f

def full_design(f):
    p=[pd.DataFrame({'const':np.ones(len(f))},index=f.index)]
    for c in ['section','row','source','qty_group','event_key','observed_day']:
        p.append(pd.get_dummies(f[c],prefix=c,drop_first=True,dtype=float))
    p.append(pd.DataFrame(spline(f.days_to_event_exact),index=f.index,columns=['h'+str(i) for i in range(5)]))
    return pd.concat(p,axis=1)

def adjusted_logs(train,application):
    X=full_design(train)
    beta,_,rank,_=lstsq(X.to_numpy(),np.log(train.price_usd_base),cond=1e-10,lapack_driver='gelsd')
    coef=dict(zip(X.columns,beta));adj=np.log(application.price_usd_base.to_numpy())
    known=np.ones(len(application),dtype=bool)
    for c in ['section','row','source','qty_group']:
        known &= application[c].isin(train[c].unique()).to_numpy()
        adj-=np.array([coef.get(c+'_'+str(v),0.) for v in application[c]])
    adj[~known]=np.nan
    return adj,int(rank),X.shape[1]

def complete_cutoff(t):
    at=t.normalize()+TD(hours=20)
    return at if at<=t else at-TD(days=1)

def build_panel(f,variant,write=True):
    eligible=f.eligible_100_common_seats & ~f.qty_invalid
    if variant=='sh_only':eligible &= f.source.eq('sh')
    if variant=='dedup':eligible &= ~f.duplicate_extra_candidate
    if variant=='under_10000':eligible &= f.price_usd_base.le(10000)
    data=f[eligible].copy().reset_index(drop=True)
    cutoffs=f.groupby('event_key').observed_at_edt.max().map(complete_cutoff).to_dict()
    events=f[['event_key','event_date','event_start_local']].drop_duplicates().sort_values('event_date')
    panel=[];training=[]
    def stats(w):
        w=w[w.adj.notna()]; n=len(w);sections=w.section.nunique();ok=n>=5 and sections>=2
        return float(w.adj.median()) if ok else np.nan,n,sections,ok
    for t in pd.date_range(FIRST,LAST,freq='D'):
        tr=data[(data.observed_at_edt<=t)&(data.observed_at_edt>t-TD(days=60))]
        if len(tr)<500:continue
        app=data[(data.observed_at_edt>t-TD(days=6))&(data.observed_at_edt<=t+TD(days=6))].copy()
        app['adj'],rank,p=adjusted_logs(tr,app)
        maxtrain=tr.observed_at_edt.max();assert maxtrain<=t
        training.append(dict(variant=variant,as_of=t,records=len(tr),rank=rank,parameters=p,max_train_time=maxtrain))
        for ev in events.itertuples(index=False):
            d=(ev.event_start_local-t).total_seconds()/86400
            if d<=3 or t>cutoffs[ev.event_key]:continue
            g=app[app.event_key.eq(ev.event_key)]
            a=g[g.observed_at_edt<=t-TD(days=3)]
            b=g[(g.observed_at_edt>t-TD(days=3))&(g.observed_at_edt<=t)]
            c=g[(g.observed_at_edt>t)&(g.observed_at_edt<=t+TD(days=3))]
            dd=g[g.observed_at_edt>t+TD(days=3)]
            la,na,sa,oka=stats(a);lb,nb,sb,okb=stats(b);lc,nc,sc,okc=stats(c);ld,nd,sd,okd=stats(dd)
            b0=b[b.split_half.eq(0)];b1=b[b.split_half.eq(1)]
            l0,n0,s0,ok0=stats(b0);l1,n1,s1,ok1=stats(b1)
            mature=t+TD(days=3)<=cutoffs[ev.event_key]
            mature6=t+TD(days=6)<=cutoffs[ev.event_key] and d>6
            r=dict(variant=variant,event_key=ev.event_key,event_date=ev.event_date,as_of=t,
                label_end=t+TD(days=3),label_end_6d=t+TD(days=6),days_to_event=d,
                event_complete_through=cutoffs[ev.event_key],seat_fit_max_time=maxtrain,seat_fit_n=len(tr),
                n_past_a=na,n_recent_b=nb,n_future_c=nc,n_future_d=nd,
                sections_a=sa,sections_b=sb,sections_c=sc,sections_d=sd,
                n_split_b0=n0,n_split_b1=n1,features_available=oka and okb,
                label_mature=mature,label_coverage=okc,
                split_features_available=oka and ok0 and ok1,
                log_a=la,log_b=lb,log_c=lc if mature else np.nan,
                x=lb-la if oka and okb else np.nan,
                y=lc-lb if mature and oka and okb and okc else np.nan,
                x_split=l0-la if oka and ok0 and ok1 else np.nan,
                y_split=lc-l1 if mature and oka and ok0 and ok1 and okc else np.nan,
                y_nonoverlap=ld-lc if mature6 and oka and okb and okc and okd else np.nan,
                sh_share_a=float(a.source.eq('sh').mean()),sh_share_b=float(b.source.eq('sh').mean()))
            panel.append(r)
        if t.day in [1,15]:print(variant,str(t.date()),'panels',len(panel),flush=True)
    out=pd.DataFrame(panel)
    # Leave-this-event-out equal-weight market factor, using only past prices.
    for xc,mc in [('x','market_x'),('x_split','market_x_split')]:
        out[mc]=np.nan;out[mc+'_n']=0
        for _,idx in out.groupby('as_of').groups.items():
            for i in idx:
                peers=out.loc[idx,xc].drop(index=i).dropna()
                out.loc[i,mc+'_n']=len(peers)
                if len(peers)>=5:out.loc[i,mc]=peers.median()
    if write:
        save(out,'panel_'+variant+'.csv');save(pd.DataFrame(training),'seat_training_'+variant+'.csv')
    return out

def regression_design(d,signal=True,expost=False,columns=None):
    d=d.reset_index(drop=True)
    X=pd.DataFrame({'const':np.ones(len(d)),'market_x':d.mx.to_numpy()})
    for j in range(5):X['h'+str(j)]=spline(d.days_to_event)[:,j]
    X=pd.concat([X,pd.get_dummies(d.event_key,prefix='event',drop_first=False,dtype=float)],axis=1)
    # Leave-one-out market factor contains -x/N when mean based; ours is a median,
    # yet date FE already controls the common factor, so omit market_x in ex-post regression.
    if expost:
        X=X.drop(columns='market_x')
        X=pd.concat([X,pd.get_dummies(d.as_of.dt.strftime('%Y-%m-%d'),prefix='day',drop_first=False,dtype=float)],axis=1)
    if signal:X['signal']=d.xx.to_numpy()
    if columns is not None:X=X.reindex(columns=columns,fill_value=0.)
    return X

def select(panel,kind):
    x='x_split' if kind=='split' else 'x'; y={'main':'y','split':'y_split','nonoverlap':'y_nonoverlap'}[kind]
    m='market_x_split' if kind=='split' else 'market_x'
    d=panel.copy();d['xx']=d[x];d['yy']=d[y];d['mx']=d[m]
    d['mature_at']=d.label_end_6d if kind=='nonoverlap' else d.label_end
    return d

def cluster_variance(X,u,groups,bread):
    G=pd.Series(groups).nunique();n,p=X.shape;meat=np.zeros((p,p))
    for g in pd.unique(groups):
        score=X[np.asarray(groups)==g].T@u[np.asarray(groups)==g];meat+=np.outer(score,score)
    rank=np.linalg.matrix_rank(X)
    return (G/(G-1))*((n-1)/(n-rank))*bread@meat@bread,G

def explanatory(panel,kind,variant):
    d=select(panel,kind).dropna(subset=['xx','yy','mx']).reset_index(drop=True)
    if len(d)<100:return dict(variant=variant,kind=kind,n=len(d),status='insufficient')
    Xdf=regression_design(d,expost=True);X=Xdf.to_numpy();y=d.yy.to_numpy()
    beta,_,rank,_=lstsq(X,y,cond=1e-10,lapack_driver='gelsd');u=y-X@beta
    pinv=np.linalg.pinv(X,rcond=1e-10);bread=pinv@pinv.T
    week=d.as_of.dt.tz_localize(None).dt.to_period('W-SUN').astype(str).to_numpy()
    event=d.event_key.to_numpy()
    ve,ge=cluster_variance(X,u,event,bread);vw,gw=cluster_variance(X,u,week,bread)
    vew,_=cluster_variance(X,u,np.array([a+'|'+b for a,b in zip(event,week)]),bread)
    j=Xdf.columns.get_loc('signal');cg=float((ve+vw-vew)[j,j]);vari=max(cg,float(ve[j,j]),float(vw[j,j]),0.)
    se=np.sqrt(vari);crit=student_t.ppf(.975,min(ge,gw)-1);b=beta[j]
    # Frisch-Waugh plot residuals; not independent out-of-sample evidence.
    Z=Xdf.drop(columns='signal').to_numpy();bx=lstsq(Z,d.xx.to_numpy(),cond=1e-10,lapack_driver='gelsd')[0];by=lstsq(Z,y,cond=1e-10,lapack_driver='gelsd')[0]
    residual=pd.DataFrame({'event_key':event,'as_of':d.as_of,'x_residual':d.xx-Z@bx,'y_residual':y-Z@by})
    save(residual,f'residuals_{variant}_{kind}.csv')
    return dict(variant=variant,kind=kind,status='estimated',n=len(d),events=ge,weeks=gw,days=d.as_of.nunique(),
        coefficient=float(b),se=float(se),lower95=float(b-crit*se),upper95=float(b+crit*se),
        p_two_sided=float(2*student_t.sf(abs(b/se),min(ge,gw)-1)),
        se_event=float(np.sqrt(max(ve[j,j],0))),se_week=float(np.sqrt(max(vw[j,j],0))),
        two_way_variance=cg,first_date=str(d.as_of.min()),last_date=str(d.as_of.max()),rank=int(rank))

def walkforward(panel,kind,variant,gap=0):
    data=select(panel,kind);pred=[]
    for t in sorted(data.as_of[data.as_of>=OOS].unique()):
        train=data[(data.mature_at<=t-TD(days=gap))].dropna(subset=['xx','yy','mx'])
        test=data[data.as_of.eq(t)].dropna(subset=['xx','mx'])
        if len(train)<120 or train.as_of.nunique()<15 or len(test)==0:continue
        assert train.mature_at.max()<=t-TD(days=gap)
        vals={}; coeff=np.nan
        for name,sig in [('baseline',False),('momentum',True)]:
            X=regression_design(train,signal=sig);Xt=regression_design(test,signal=sig,columns=X.columns)
            # Center event effects on the training population. An event with no
            # matured return label gets the pooled effect, not an arbitrary FE reference.
            ec=[c for c in X.columns if c.startswith('event_')]
            em=X[ec].mean();X[ec]=X[ec]-em;Xt[ec]=Xt[ec]-em
            new_event=~test.event_key.isin(train.event_key.unique()).to_numpy()
            Xt.loc[new_event,ec]=0.
            beta=lstsq(X.to_numpy(),train.yy.to_numpy(),cond=1e-10,lapack_driver='gelsd')[0]
            vals[name]=Xt.to_numpy()@beta
            if sig:coeff=beta[X.columns.get_loc('signal')]
        for j,row in enumerate(test.itertuples(index=False)):
            pred.append(dict(variant=variant,kind=kind,gap_days=gap,event_key=row.event_key,event_date=row.event_date,
                as_of=row.as_of,mature_at=row.mature_at,days_to_event=row.days_to_event,xx=row.xx,mx=row.mx,yy=row.yy,
                prediction_zero=0.,prediction_baseline=vals['baseline'][j],prediction_momentum=vals['momentum'][j],
                training_n=len(train),training_max_label_end=train.mature_at.max(),signal_coefficient=coeff,
                scorable=bool(np.isfinite(row.yy)),event_in_training=row.event_key in set(train.event_key)))
    out=pd.DataFrame(pred);save(out,f'predictions_{variant}_{kind}_gap{gap}.csv')
    return out

def bootstrap_loss(p):
    # Calendar-day moving block bootstrap retains the entire cross-section each day.
    pp=p.copy(); pp['loss_delta']=(pp.yy-pp.prediction_momentum).abs()-(pp.yy-pp.prediction_baseline).abs()
    daily=pp.groupby('as_of').loss_delta.agg(['sum','size']).sort_index()
    dates=pd.date_range(daily.index.min(),daily.index.max(),freq='D');daily=daily.reindex(dates,fill_value=0.)
    a=daily.to_numpy();n=len(a);rng=np.random.default_rng(20260928);vals=[]
    for _ in range(2000):
        starts=rng.integers(0,n,size=int(np.ceil(n/7)))
        ids=np.concatenate([(s+np.arange(7))%n for s in starts])[:n]
        sums=a[ids].sum(axis=0)
        if sums[1]>0:vals.append(sums[0]/sums[1]*100)
    return [float(v) for v in np.quantile(vals,[.025,.975])]

def metrics(pred,variant,kind,gap):
    if pred.empty:return []
    p=pred[pred.scorable].copy();ci=bootstrap_loss(p) if len(p) else [np.nan,np.nan]
    rows=[]
    for name in ['zero','baseline','momentum']:
        err=p['prediction_'+name]-p.yy
        direction=((p['prediction_'+name]<0)==(p.yy<0)).mean() if name!='zero' else np.nan
        rows.append(dict(variant=variant,kind=kind,gap_days=gap,model=name,n=len(p),issued=len(pred),
            unscorable=len(pred)-len(p),events=p.event_key.nunique(),days=p.as_of.nunique(),
            mae_log_pp=float(err.abs().mean()*100),rmse_log_pp=float(np.sqrt((err**2).mean())*100),
            directional_accuracy=float(direction),actual_down_share=float((p.yy<0).mean()),
            first_date=str(p.as_of.min()),last_date=str(p.as_of.max()),
            delta_mae_log_pp=float(((p.yy-p.prediction_momentum).abs()-(p.yy-p.prediction_baseline).abs()).mean()*100),
            delta_mae_ci_lower=ci[0],delta_mae_ci_upper=ci[1]))
    # Same models, same rows by time period, event, and countdown range.
    p['period']=p.as_of.dt.strftime('%Y-%m')
    p['countdown_band']=pd.cut(p.days_to_event,[3,7,14,30,60,np.inf],labels=['3-7d','7-14d','14-30d','30-60d','60+d'])
    groups=[]
    for field in ['period','event_date','countdown_band']:
        for val,g in p.groupby(field,observed=True):
            groups.append(dict(group_by=field,group=str(val),n=len(g),mae_baseline=float((g.yy-g.prediction_baseline).abs().mean()*100),
                mae_momentum=float((g.yy-g.prediction_momentum).abs().mean()*100),mean_past_return=float(g.xx.mean()),mean_future_return=float(g.yy.mean())))
    save(pd.DataFrame(groups),f'oos_subgroups_{variant}_{kind}_gap{gap}.csv')
    # Conditional down frequency versus SAME countdown band, descriptive only.
    probs=[]
    for val,g in p.groupby('countdown_band',observed=True):
        pastdown=g[g.xx<0]
        probs.append(dict(countdown_band=str(val),n=len(g),n_past_down=len(pastdown),unconditional_future_down=float((g.yy<0).mean()),
            future_down_given_past_down=float((pastdown.yy<0).mean()) if len(pastdown) else np.nan))
    save(pd.DataFrame(probs),f'down_probabilities_{variant}_{kind}_gap{gap}.csv')
    return rows

def plot(coefs,metrics_df):
    fig,axs=plt.subplots(1,2,figsize=(12,5.3),layout='constrained')
    names=[('all_sources','main','Shared endpoint'),('all_sources','split','Split endpoint'),('all_sources','nonoverlap','Separate windows (6d)'),('sh_only','main','SH only')]
    for i,(v,k,label) in enumerate(names):
        r=coefs[(coefs.variant==v)&(coefs.kind==k)].iloc[0]
        axs[0].errorbar(r.coefficient,i,xerr=[[r.coefficient-r.lower95],[r.upper95-r.coefficient]],fmt='o',color='#2264a6',capsize=4)
    axs[0].set_yticks(range(len(names)),[x[2] for x in names]);axs[0].invert_yaxis();axs[0].axvline(0,color='#667085',ls='--')
    axs[0].set_xlabel('Past-return slope (95% exploratory interval)');axs[0].set_title('A. Conditional association',loc='left',fontweight='bold')
    main=metrics_df[(metrics_df.variant=='all_sources')&(metrics_df.kind=='main')&(metrics_df.gap_days==0)]
    vals=main.set_index('model').loc[['zero','baseline','momentum'],'mae_log_pp']
    bars=axs[1].bar(['No change','Baseline','Baseline + past return'],vals,color=['#98a2b3','#175c9e','#c87420'])
    axs[1].bar_label(bars,fmt='%.2f',padding=4);axs[1].set_ylim(0,vals.max()*1.2)
    axs[1].set_ylabel('Out-of-sample MAE (log percentage points)');axs[1].set_title('B. Rolling forecast error',loc='left',fontweight='bold')
    axs[1].tick_params(axis='x',labelsize=9)
    for a in axs:a.spines[['right','top']].set_visible(False);a.grid(axis='y',alpha=.15)
    fig.suptitle('Harry Styles / MSG / 100 Level: does a 3-day decline continue?',fontweight='bold',fontsize=14)
    fig.text(.02,-.04,'Positive slope supports continuation; negative slope indicates reversal in the estimated window prices.\nHistorical, overlapping windows; no fees, executable quotes, fills, or trading PnL.',fontsize=9,color='#475467')
    fig.savefig(ROOT/'figures/q2_results.png',dpi=180,bbox_inches='tight');plt.close(fig)

def run():
    f=load();coefs=[];metr=[];coverage=[]
    for variant in ['all_sources','sh_only','dedup','under_10000']:
        panel=build_panel(f,variant)
        kinds=['main','split','nonoverlap'] if variant in ['all_sources','sh_only'] else ['main']
        for kind in kinds:
            print('estimating',variant,kind,flush=True)
            coefs.append(explanatory(panel,kind,variant))
            pred=walkforward(panel,kind,variant);metr.extend(metrics(pred,variant,kind,0))
            d=select(panel,kind); valid=d.xx.notna()&d.mx.notna()
            coverage.append(dict(variant=variant,kind=kind,candidate_event_days=len(d),feature_eligible=int(valid.sum()),
                labeled=int((valid&d.yy.notna()).sum()),missing_future=int((valid&d.yy.isna()).sum())))
        if variant=='all_sources':
            pred=walkforward(panel,'main',variant,gap=6);metr.extend(metrics(pred,variant,'main',6))
            primary=walkforward(panel,'main',variant)
            pending=primary[primary.as_of.eq(LAST)].copy();pending['status']='historical_snapshot_not_prospectively_issued_at_as_of'
            save(pending,'latest_research_signals_not_trade_orders.csv')
    c=pd.DataFrame(coefs);m=pd.DataFrame(metr);save(c,'conditional_coefficients.csv');save(m,'oos_metrics.csv');save(pd.DataFrame(coverage),'sample_coverage.csv')
    plot(c,m)
    (ROOT/'processed/model_summary.json').write_text(json.dumps({'coefficients':coefs,'metrics':metr,'coverage':coverage},ensure_ascii=False,indent=2,default=str))
    print(c.to_string(index=False));print(m.to_string(index=False))

if __name__=='__main__':run()

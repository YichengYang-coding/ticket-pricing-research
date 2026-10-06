from pathlib import Path
import os,json,hashlib
import numpy as np
import pandas as pd
from scipy.linalg import solve

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'outputs'
INPUT=ROOT/'input/Harry_cleaned_sales.csv'
if not INPUT.exists():INPUT=ROOT.parent/'msg_seat_study/data/Harry_cleaned_sales.csv'
def csv(df,name):
    p=OUT/name;tmp=p.with_suffix(p.suffix+'.tmp');df.to_csv(tmp,index=False);os.replace(tmp,p)
raw=pd.read_csv(INPUT,low_memory=False)
d=raw[raw.included_in_research & raw.source.eq('sh') & raw.Section.astype(str).str.fullmatch(r'10[1-9]|11[0-9]|120') & raw.valid_prestart & raw.price_usd_base.gt(0)].copy()
d['r']=pd.to_numeric(d.Row,errors='coerce');special=d[d.r.between(1,2)]
d=d[d.r.between(3,22)&d.r.eq(d.r.round())].copy();d['r']=d.r.astype(int);d['s']=pd.to_numeric(d.Section).astype(int)
d['ts']=pd.to_datetime(d.observed_at_utc,utc=True);d['event_start']=pd.to_datetime(d.event_start_utc,utc=True)
d['event']=d.event_date.astype(str);d['q']=d.qty_group.astype(str);d['price']=d.price_usd_base.astype(float)
d['band']=pd.cut(d.r,[2,6,10,15,22],labels=['3-6','7-10','11-15','16-22']).astype(str)
d=d.sort_values(['ts','record_key']).reset_index(drop=True)
events=sorted(d.event.unique());sections=list(range(101,121));quantities=['unknown','1','2','3','4','5plus']
assert set(d.q).issubset(quantities)
# Categories come from known event and seat metadata; no estimated full-history effects are reused.
def design(f,origin):
    n=len(f);cols={'intercept':np.ones(n)};pen=[1e-8]
    def add(name,arr,lam):cols[name]=np.asarray(arr,float);pen.append(lam)
    add('row_slope',(f.r-15)/10,1)
    add('front_extra',np.maximum(6-f.r,0)/3,1)
    lead=(f.event_start-f.ts).dt.total_seconds().to_numpy()/86400
    u=np.log1p(np.maximum(lead,0));add('log_days',u,1)
    for knot in [1,4,7,14,30]:add('log_days_hinge_'+str(knot),np.maximum(u-np.log1p(knot),0),1)
    add('calendar_trend',(f.ts-origin).dt.total_seconds().to_numpy()/86400/14,1)
    for s in sections[1:]:add('section_'+str(s),f.s.eq(s),2)
    for e in events[1:]:add('event_'+e,f.event.eq(e),3)
    for q in quantities[1:]:add('quantity_'+q,f.q.eq(q),2)
    for s in sections[1:]:add('section_row_'+str(s),f.s.eq(s)*(f.r-15)/10,20)
    return np.column_stack(list(cols.values())),list(cols),np.asarray(pen)

def fit(train,origin):
    X,names,pen=design(train,origin);y=np.log(train.price.to_numpy())
    age=(origin-train.ts).dt.total_seconds().to_numpy()/86400
    base=np.exp2(-age/14);base*=len(base)/base.sum();w=base.copy()
    b=np.zeros(X.shape[1]);b[0]=np.median(y)
    for it in range(30):
        error=y-X@b;w=base*np.minimum(1,.25/np.maximum(abs(error),1e-12))
        gram=X.T@(X*w[:,None])+np.diag(pen)
        bn=solve(gram,X.T@(w*y),assume_a='pos')
        if max(abs(bn-b))<1e-6:b=bn;break
        b=bn
    return b,names,it+1

def baselines(train,test,origin):
    recent72=train[train.ts.ge(origin-pd.Timedelta(hours=72))]
    recent7=train[train.ts.ge(origin-pd.Timedelta(days=7))]
    rules=[('exact72',recent72,['event','s','band']),('exact7',recent7,['event','s','band']),('section7',recent7,['event','s']),('event7',recent7,['event'])]
    maps={}
    for label,frame,keys in rules:
        a=frame.groupby(keys).price.agg(['median','size'])
        maps[label]=(keys,a[a['size'].ge(5)])
    results=[]
    for row in test.itertuples():
        z={'strict_median':np.nan,'strict_n':0,'fallback_median':np.nan,'fallback_n':0,'fallback_rule':'unavailable'}
        for label,_,_ in rules:
            keys,tab=maps[label];key=tuple(getattr(row,k) for k in keys);key=key[0] if len(keys)==1 else key
            if key in tab.index:
                hit=tab.loc[key];value=float(hit['median']);count=int(hit['size'])
                if label=='exact72':z['strict_median']=value;z['strict_n']=count
                if not np.isfinite(z['fallback_median']):z['fallback_median']=value;z['fallback_n']=count;z['fallback_rule']=label
        results.append(z)
    return pd.DataFrame(results,index=test.index)

predictions=[];origin_rows=[]
for date in pd.date_range('2026-09-01','2026-09-27',freq='D'):
    origin=date.tz_localize('America/New_York').tz_convert('UTC');end=origin+pd.Timedelta(days=1)
    train=d[d.ts.lt(origin)&d.ts.ge(origin-pd.Timedelta(days=90))]
    test=d[d.ts.ge(origin)&d.ts.lt(end)].copy()
    counts=train.groupby('event').size()
    test=test[test.event.map(counts).fillna(0).ge(30)].copy()
    if test.empty:continue
    coef,names,it=fit(train,origin);X,_,_=design(test,origin)
    test['model_price']=np.exp(X@coef);test['origin']=str(origin)
    bb=baselines(train,test,origin);test=pd.concat([test,bb],axis=1)
    predictions.append(test[['record_key','event','ts','s','r','q','band','price','model_price','origin','strict_median','strict_n','fallback_median','fallback_n','fallback_rule']])
    origin_rows.append({'origin':str(origin),'train_n':len(train),'test_n':len(test),'iterations':it,'strict_covered':int(test.strict_median.notna().sum()),'fallback_covered':int(test.fallback_median.notna().sum())})
p=pd.concat(predictions,ignore_index=True);csv(p,'replay_predictions.csv');csv(pd.DataFrame(origin_rows),'replay_origins.csv')
metrics=[]
def summarize(frame,col,label,scope):
    e=frame[col]-frame.price;ape=abs(e)/frame.price
    by=frame.assign(ae=abs(e)).groupby('event').ae.mean()
    return {'scope':scope,'method':label,'n':len(frame),'events':frame.event.nunique(),'mae_usd':float(abs(e).mean()),'median_ape_pct':float(100*ape.median()),'median_signed_pct':float(100*(e/frame.price).median()),'mean_event_mae_usd':float(by.mean())}
metrics.append(summarize(p,'model_price','model','all_model_predictions'))
for col,label in [('strict_median','strict_72h'),('fallback_median','hierarchical_median')]:
    f=p[p[col].notna()]
    if len(f):
        metrics.append(summarize(f,'model_price','model',label+'_shared'))
        metrics.append(summarize(f,col,label,label+'_shared'))
m=pd.DataFrame(metrics);csv(m,'metrics.csv')
daily=[]
for origin,f in p.groupby('origin'):
    for col,label in [('strict_median','strict_72h'),('fallback_median','hierarchical_median')]:
        g=f[f[col].notna()]
        if len(g):daily.append({'origin':origin,'benchmark':label,'n':len(g),'model_mae':abs(g.model_price-g.price).mean(),'baseline_mae':abs(g[col]-g.price).mean()})
csv(pd.DataFrame(daily),'daily_comparisons.csv')
origin=pd.Timestamp('2026-09-28 18:00',tz='America/New_York').tz_convert('UTC')
train=d[d.ts.lt(origin)&d.ts.ge(origin-pd.Timedelta(days=90))];coef,names,it=fit(train,origin)
csv(pd.DataFrame({'term':names,'coefficient':coef}),'final_coefficients.csv')
examples=[]
for section,row in [(102,6),(102,15),(107,6),(107,15),(107,20),(117,15),(106,10),(118,10)]:
    examples.append({'event':'2026-09-30','event_start':pd.Timestamp('2026-09-30 20:00',tz='America/New_York').tz_convert('UTC'),'ts':origin,'s':section,'r':row,'q':'2','band':'3-6' if row<=6 else '7-10' if row<=10 else '11-15' if row<=15 else '16-22'})
ex=pd.DataFrame(examples);X,_,_=design(ex,origin);ex['model_price']=np.exp(X@coef);ex=pd.concat([ex,baselines(train,ex,origin)],axis=1);csv(ex,'comparable_examples.csv')
audit={'input_sha256':hashlib.sha256(INPUT.read_bytes()).hexdigest(),'input_rows':len(raw),'universe_rows':len(d),'events':len(events),'sparse_rows_1_2_excluded':len(special),'replay_origins':len(origin_rows),'replay_rows':len(p),'strict_coverage_pct':100*p.strict_median.notna().mean(),'fallback_coverage_pct':100*p.fallback_median.notna().mean(),'snapshot_origin':str(origin),'final_training_rows':len(train),'final_training_max_timestamp':str(train.ts.max()),'models':'single specification; no hyperparameter search','evaluation_status':'retrospective rolling time replay; design informed by previously inspected history'}
for col,name in [('strict_median','strict'),('fallback_median','fallback')]:
    g=p[p[col].notna()];audit[name+'_model_win_pct']=float(100*(abs(g.model_price-g.price)<abs(g[col]-g.price)).mean())
    dt=pd.DataFrame(daily);dt=dt[dt.benchmark.eq('strict_72h' if name=='strict' else 'hierarchical_median')];audit[name+'_days_model_better']=int((dt.model_mae<dt.baseline_mae).sum());audit[name+'_days_compared']=len(dt)
(OUT/'audit.json').write_text(json.dumps(audit,indent=2))
assert (pd.to_datetime(p.ts,utc=True)>=pd.to_datetime(p.origin,utc=True)).all()
assert (pd.to_datetime(p.ts,utc=True)<pd.to_datetime(p.origin,utc=True)+pd.Timedelta(days=1)).all()
assert p.record_key.is_unique
assert np.isfinite(p.model_price).all() and p.model_price.gt(0).all()
assert len(pd.read_csv(OUT/'replay_predictions.csv'))==len(p)
print(json.dumps(audit,indent=2));print(m.round(3).to_string(index=False));print(ex[['s','r','model_price','strict_median','strict_n','fallback_median','fallback_rule']].round(2).to_string(index=False))

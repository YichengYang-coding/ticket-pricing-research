"""Retrospective price and observed-record activity association; scipy, no statsmodels."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy import linalg,stats,optimize
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

R=Path(__file__).resolve().parent;P=R/'processed';F=R/'figures';F.mkdir(exist_ok=True)
d=pd.read_csv(P/'sales_cleaned_all_records.csv',keep_default_na=False)
ev=pd.read_csv(P/'event_manifest.csv')
d['observed']=pd.to_datetime(d.observed_at_utc,utc=True).dt.tz_convert('America/Los_Angeles')
d['start']=pd.to_datetime(d.event_start_utc,utc=True).dt.tz_convert('America/Los_Angeles')
d['weekday']=d.start.dt.day_name();d['order10']=d.order/10
d['sale_week']=d.observed.dt.tz_localize(None).dt.to_period('W-SUN').astype(str)
d['event_week']=d.start.dt.tz_localize(None).dt.to_period('W-SUN').astype(str)
d['cohort']=d.event_date.map(ev.set_index('event_date').announcement_cohort)
d['post_0810']=(d.observed>=pd.Timestamp('2026-08-10',tz='America/Los_Angeles')).astype(int)
d['cell']=d.section.astype(str)+'_'+d.row.astype(str)
d['zone_row']=d.zone.astype(str)+'_'+d.row.astype(str)
def save(g,name):g.to_csv(P/name,index=False,encoding='utf-8-sig')
def window(lo=7,hi=14,shift=0):
 g=d.copy();g['lead']=g.days_to_event_exact+shift/24
 g['lead_bucket']=np.ceil(g.lead).astype(int).astype(str)
 g=g[g.valid_prestart&g.source.eq('sh')&g.lead.gt(lo)&g.lead.le(hi)].copy()
 # Coverage reach, not a monitoring guarantee. All events completed, last records beyond scheduled time.
 for _,e in ev.iterrows():
  h=d[d.event_date.eq(e.event_date)&d.source.eq('sh')];s=h.start.iloc[0]+pd.Timedelta(hours=shift)
  assert h.observed.min()<=s-pd.Timedelta(days=hi)
  assert h.observed.max()>=s-pd.Timedelta(days=lo)
 return g
def design(g,cats,extra=()):
 x=pd.DataFrame({'intercept':1.,'order10':g.order10},index=g.index)
 if cats:x=pd.concat([x,pd.get_dummies(g[cats].astype(str),drop_first=True,dtype=float)],axis=1)
 for c in extra:x[c]=g[c].astype(float)
 return x
def meat(score,labels,rank):
 code,groups=pd.factorize(labels);G=len(groups);n,k=score.shape;s=np.zeros((G,k));np.add.at(s,code,score)
 return s.T@s*(G/(G-1))*((n-1)/(n-rank)),G
prices=[];counts=[]
def price_fit(raw,label,cell=False,allreserved=False,extra=(),cohort=False,save_main=False):
 g=raw[raw.other_reserved_seat if allreserved else raw.ordinary100_seat].copy()
 cats=(['cell'] if cell else ['section','zone_row' if allreserved else 'row'])+['qty_group','lead_bucket','weekday']
 if cohort:cats+=['cohort']
 x=design(g,cats,extra)
 if allreserved and not cell:
  # Section already identifies level, so each level needs its own baseline row.
  for zone in sorted(g.zone.unique())[1:]:
   baseline=sorted(g.loc[g.zone.eq(zone),'zone_row'].unique())[0]
   x=x.drop(columns=['zone_row_'+baseline],errors='ignore')
 X=x.to_numpy(float);y=np.log(g.price_usd_base.to_numpy(float))
 w=(1/g.groupby('event_date').event_date.transform('size')).to_numpy();Xw=X*np.sqrt(w)[:,None]
 b,_,rank,sv=linalg.lstsq(Xw,y*np.sqrt(w),cond=1e-10,lapack_driver='gelsd')
 assert rank==X.shape[1],(label,rank,X.shape)
 u=y-X@b;bread=np.linalg.pinv(Xw.T@Xw,rcond=1e-10);score=X*(w*u)[:,None]
 a,G=meat(score,g.event_date,rank);c,H=meat(score,g.sale_week,rank);ac,J=meat(score,g.event_date+'|'+g.sale_week,rank)
 variances=[float((bread@v@bread)[1,1]) for v in [a,c,a+c-ac]]
 se=np.sqrt(max(variances+[0.]));df=min(G,H)-1;ci=b[1]+np.array([-1,1])*stats.t.ppf(.975,df)*se
 r=dict(model=label,n_records=len(g),n_events=G,n_sale_weeks=H,rank=int(rank),beta=float(b[1]),se=float(se),df=df,pct_per_10=float(np.expm1(b[1])*100),ci_low_pct=float(np.expm1(ci[0])*100),ci_high_pct=float(np.expm1(ci[1])*100),p=float(2*stats.t.sf(abs(b[1]/se),df)))
 prices.append(r)
 if save_main:
  g['adjusted_log_price']=y-(X@b-b[0]-X[:,1]*b[1])
  ix=g.groupby(['event_date','order']).agg(n_price=('record_key','size'),raw_median_usd=('price_usd_base','median'),adjusted_log_mean=('adjusted_log_price','mean')).reset_index()
  baseline=np.exp(ix.loc[ix.order.le(6),'adjusted_log_mean']).mean()
  ix['adjusted_index']=100*np.exp(ix.adjusted_log_mean)/baseline
  ix['fitted_index']=100*np.exp(b[0]+b[1]*ix.order/10)/baseline
  save(ix,'price_event_indices.csv');save(pd.DataFrame({'term':x.columns,'coefficient':b}),'price_coefficients.csv')
  save(g[['record_key','event_date','order','observed_at_utc','section','row','qty_group','lead','price_usd_base','adjusted_log_price']],'price_main_records.csv')
  assert np.allclose(pd.Series(w,index=g.index).groupby(g.event_date).sum(),1)
 return r
def count_table(raw,lo=7,hi=14):
 rows=[]
 for date,h in raw.groupby('event_date'):
  g=h[h.ordinary100_seat];s=h.start.iloc[0];t=np.sort(h.observed.astype('int64').to_numpy()/3.6e12)
  edges=np.r_[(s-pd.Timedelta(days=hi)).value/3.6e12,t,(s-pd.Timedelta(days=lo)).value/3.6e12]
  rows.append(dict(event_date=date,order=h.order.iloc[0],order10=h.order10.iloc[0],weekday=h.weekday.iloc[0],event_week=h.event_week.iloc[0],ordinary100_count=len(g),allzone_count=len(h),other_reserved_count=int(h.other_reserved_seat.sum()),ordinary_share=len(g)/len(h),exposure_days=hi-lo,days_with_record=h.lead_bucket.nunique(),all_days_observed=h.lead_bucket.nunique()==hi-lo,max_observed_gap_hours=np.diff(edges).max(),qty_unknown=int(g.qty_unknown.sum()),cohort=h.cohort.iloc[0]))
 return pd.DataFrame(rows).sort_values('order')
def count_fit(a,label,outcome='ordinary100_count',cohort=False,save_main=False):
 a=a.copy();x=design(a,['weekday']+(['cohort'] if cohort else []));X=x.to_numpy(float);y=a[outcome].to_numpy(float);n,k=X.shape
 assert np.linalg.matrix_rank(X)==k
 def fn(b):
  z=X@b;mu=np.exp(z);return np.sum(mu-y*z),X.T@(mu-y)
 b0=np.zeros(k);b0[0]=np.log(y.mean());fit=optimize.minimize(fn,b0,jac=True,method='BFGS',options={'gtol':1e-8,'maxiter':2000})
 b=fit.x;mu=np.exp(X@b);assert np.abs(fn(b)[1]).max()<1e-4,(label,fit.message)
 bread=np.linalg.pinv(X.T@(mu[:,None]*X));score=X*(y-mu)[:,None]
 m,G=meat(score,a.event_week,k);disp=max(1.,np.sum((y-mu)**2/mu)/(n-k))
 variances=[float((bread@m@bread)[1,1]),float((bread@score.T@score@bread*n/(n-k))[1,1]),float(bread[1,1]*disp)]
 se=np.sqrt(max(variances+[0.]));df=G-1;ci=b[1]+np.array([-1,1])*stats.t.ppf(.975,df)*se
 r=dict(model=label,outcome=outcome,n_events=n,n_records=int(y.sum()),n_event_weeks=G,beta=float(b[1]),se=float(se),df=df,dispersion=float(disp),pct_per_10=float(np.expm1(b[1])*100),ci_low_pct=float(np.expm1(ci[0])*100),ci_high_pct=float(np.expm1(ci[1])*100),p=float(2*stats.t.sf(abs(b[1]/se),df)))
 counts.append(r)
 if save_main:
  a['fitted_count']=mu;save(a,'activity_main_events.csv');save(pd.DataFrame({'term':x.columns,'coefficient':b}),'activity_coefficients.csv')
 return r

raw=window();price_fit(raw,'primary_7_14',save_main=True);a=count_table(raw);count_fit(a,'primary_7_14',save_main=True)
price_fit(raw,'exact_section_row',cell=True)
price_fit(raw[raw.order.between(2,20)],'exclude_first_last')
price_fit(raw[~raw.duplicate_extra_candidate],'dedup_candidates')
price_fit(raw[~raw.price_extreme_review&~raw.price_above_10000_review],'exclude_price_flags')
price_fit(raw[~raw.qty_unknown],'known_qty_only')
price_fit(raw[pd.to_numeric(raw.row_num,errors='coerce').le(22)],'rows_12_22')
price_fit(raw,'levels_200_400',allreserved=True)
price_fit(raw,'announcement_cohort_control',cohort=True)
price_fit(raw,'post_aug10_control',extra=['post_0810'])
count_fit(a[a.order.between(2,20)],'exclude_first_last')
count_fit(count_table(raw[~raw.duplicate_extra_candidate]),'dedup_candidates')
count_fit(a,'all_zones',outcome='allzone_count')
count_fit(a,'levels_200_400',outcome='other_reserved_count')
count_fit(a,'announcement_cohort_control',cohort=True)
count_fit(a[a.all_days_observed],'all_days_presence_proxy')
for lo,hi in [(0,7),(14,21),(21,28)]:
 g=window(lo,hi);price_fit(g,f'window_{lo}_{hi}');aa=count_table(g,lo,hi);count_fit(aa,f'window_{lo}_{hi}');save(aa,f'activity_window_{lo}_{hi}.csv')
for shift in [-1,1]:price_fit(window(shift=shift),f'start_shift_{shift:+d}h')
save(pd.DataFrame(prices),'price_models.csv');save(pd.DataFrame(counts),'activity_models.csv')
ix=pd.read_csv(P/'price_event_indices.csv');aa=pd.read_csv(P/'activity_main_events.csv')
merged=aa.merge(ix.drop(columns=['order']),on='event_date');save(merged,'BSB_event_summary.csv')
quality={f:int(raw.loc[raw.ordinary100_seat,f].sum()) for f in ['qty_unknown','duplicate_extra_candidate','price_extreme_review','price_above_10000_review']}
s=dict(raw_rows=len(d),events=len(ev),primary_price=prices[0],primary_activity=counts[0],primary_quality=quality,primary_allzone_records=int(a.allzone_count.sum()),all_days_observed=int(a.all_days_observed.sum()),max_gap_range=[float(a.max_observed_gap_hours.min()),float(a.max_observed_gap_hours.max())],first6_index=float(merged.loc[merged.order.le(6),'adjusted_index'].mean()),last6_index=float(merged.loc[merged.order.gt(15),'adjusted_index'].mean()),first6_count=float(a.loc[a.order.le(6),'ordinary100_count'].mean()),last6_count=float(a.loc[a.order.gt(15),'ordinary100_count'].mean()))
(P/'summary.json').write_text(json.dumps(s,ensure_ascii=False,indent=2))
assert a.ordinary100_count.sum()==len(pd.read_csv(P/'price_main_records.csv'))
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':150})
fig,axes=plt.subplots(2,1,figsize=(11,8),sharex=True,layout='constrained')
axes[0].plot(ix.order,ix.adjusted_index,'o-',color='#246B83',label='Adjusted price index')
axes[0].plot(ix.order,ix.fitted_index,'--',color='#C47722',label='Linear order association')
axes[0].axhline(100,color='#bbb',lw=.7);axes[0].set(ylabel='Index (first 6 mean = 100)',title='Backstreet Boys / Sphere / sh / numeric 100 Level seats / 7-14 days before show');axes[0].legend()
axes[1].bar(a.order,a.ordinary100_count,color='#246B83',alpha=.8,label='Observed records')
axes[1].plot(aa.order,aa.fitted_count,'o--',color='#C47722',label='Weekday-adjusted fit')
axes[1].set(ylabel='Records per 7-day window',xlabel='Summer show order (not whole residency order)');axes[1].legend(loc='upper left')
axes[1].set_xticks(ix.order);axes[1].set_xticklabels([f'{int(x)}\n{z[5:]}' for x,z in zip(ix.order,ix.event_date)],fontsize=8)
fig.savefig(F/'bsb_main.png',bbox_inches='tight');plt.close(fig)
fig,axes=plt.subplots(1,2,figsize=(12,6),layout='constrained')
for ax,models,title in zip(axes,[prices,counts],['Adjusted prices','Observed activity']):
 q=pd.DataFrame(models).iloc[::-1];y=np.arange(len(q));ax.errorbar(q.pct_per_10,y,xerr=np.array([q.pct_per_10-q.ci_low_pct,q.ci_high_pct-q.pct_per_10]),fmt='o',capsize=3,color='#246B83');ax.axvline(0,color='#999',lw=.8);ax.set_yticks(y);ax.set_yticklabels(q.model,fontsize=7);ax.set(title=title,xlabel='% per 10 later shows; exploratory 95% CI')
fig.savefig(F/'bsb_sensitivity.png',bbox_inches='tight');plt.close(fig)
print(json.dumps(s,indent=2));print(pd.DataFrame(prices)[['model','n_records','pct_per_10','ci_low_pct','ci_high_pct']].to_string(index=False));print(pd.DataFrame(counts)[['model','n_records','pct_per_10','ci_low_pct','ci_high_pct']].to_string(index=False))

"""Same estimators as BSB, adapted to incomplete Harry observation windows."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy import linalg,stats,optimize
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent;P=R/'processed';F=R/'figures'
d=pd.read_csv(P/'research_accepted_records.csv',keep_default_na=False,low_memory=False)
d['observed']=pd.to_datetime(d.observed_at_utc,utc=True).dt.tz_convert('America/New_York')
d['start']=pd.to_datetime(d.event_start_utc,utc=True).dt.tz_convert('America/New_York')
d['weekday']=d.start.dt.day_name();d['order10']=d.order/10
d['sale_week']=d.observed.dt.tz_localize(None).dt.to_period('W-SUN').astype(str)
d['event_week']=d.start.dt.tz_localize(None).dt.to_period('W-SUN').astype(str)
d['cohort']=np.select([d.order.le(10),d.order.le(20)],['Jan30_11ET','Jan30_14ET'],default='Feb04_11ET')
d['post_0910']=(d.observed>=pd.Timestamp('2026-09-10',tz='America/New_York')).astype(int)
d['cell']=d.section.astype(str)+'_'+d.row.astype(str)
d['zone_row']=d.zone.astype(str)+'_'+d.row.astype(str)
def save(g,name):g.to_csv(P/name,index=False,encoding='utf-8-sig')
erows=[]
for date,g in d.groupby('event_date'):
 h=g[g.source.eq('sh')];last=g.observed.max();cut=last.normalize()+pd.Timedelta(hours=20)
 if cut>last:cut-=pd.Timedelta(days=1)
 erows.append(dict(event_date=date,order=g.order.iloc[0],start=g.start.iloc[0],weekday=g.weekday.iloc[0],event_week=g.event_week.iloc[0],last_record=last,conservative_cutoff=cut,first_sh_record=h.observed.min(),completed=g.order.iloc[0]<=15,source_file=g.source_file.iloc[0]))
ev=pd.DataFrame(erows).sort_values('order');save(ev,'event_manifest.csv')
def window(lo=7,hi=14,shift=0):
 global wm
 wm=ev.copy();wm['window_start']=wm.start+pd.Timedelta(hours=shift)-pd.Timedelta(days=hi);wm['window_end']=wm.start+pd.Timedelta(hours=shift)-pd.Timedelta(days=lo)
 wm['complete_window_proxy']=(wm.conservative_cutoff>=wm.window_end)&(wm.first_sh_record<=wm.window_start)
 g=d.copy();g['lead']=g.days_to_event_exact+shift/24
 g['lead_bucket']=np.ceil(g.lead).astype(int).astype(str)
 g=g[g.valid_prestart&g.source.eq('sh')&g.lead.gt(lo)&g.lead.le(hi)&g.event_date.isin(wm.loc[wm.complete_window_proxy,'event_date'])].copy()
 if shift==0:save(wm,f'window_eligibility_{lo}_{hi}.csv')
 return g
def count_table(raw,lo=7,hi=14):
 rows=[]
 for e in wm[wm.complete_window_proxy].itertuples():
  h=raw[raw.event_date.eq(e.event_date)];g=h[h.ordinary100_seat]
  t=np.sort(h.observed.astype('int64').to_numpy()/3.6e12);edges=np.r_[e.window_start.value/3.6e12,t,e.window_end.value/3.6e12]
  cohort='Jan30_11ET' if e.order<=10 else ('Jan30_14ET' if e.order<=20 else 'Feb04_11ET')
  rows.append(dict(event_date=e.event_date,order=e.order,order10=e.order/10,weekday=e.weekday,event_week=e.event_week,ordinary100_count=len(g),allzone_count=len(h),other_reserved_count=int(h.other_reserved_seat.sum()),ordinary_share=len(g)/len(h) if len(h) else np.nan,exposure_days=hi-lo,days_with_record=h.lead_bucket.nunique(),all_days_observed=h.lead_bucket.nunique()==hi-lo,max_observed_gap_hours=np.diff(edges).max(),qty_unknown=int(g.qty_unknown.sum()),cohort=cohort,window_start=str(e.window_start),window_end=str(e.window_end),cutoff=str(e.conservative_cutoff)))
 return pd.DataFrame(rows).sort_values('order')
prices=[];counts=[]
exec(compile((R/'model_functions.py').read_text(),str(R/'model_functions.py'),'exec'))
raw=window();price_fit(raw,'primary_7_14',save_main=True);a=count_table(raw);count_fit(a,'primary_7_14',save_main=True)
price_fit(raw,'exact_section_row',cell=True)
for label,mask in [('completed_first15',raw.order.le(15)),('exclude_opening',raw.order.ne(1)),('exclude_observed_endpoints',raw.order.between(2,16)),('dedup_candidates',~raw.duplicate_extra_candidate),('exclude_price_flags',~raw.price_extreme_review&~raw.price_above_10000_review),('known_qty_only',~raw.qty_unknown),('front_rows_1_11',pd.to_numeric(raw.row_num,errors='coerce').le(11))]:
 price_fit(raw[mask],label)
price_fit(raw,'levels_200_400',allreserved=True)
price_fit(raw,'post_sep10_control',extra=['post_0910'])
price_fit(raw,'onsale_batch_control',cohort=True)
count_fit(a,'onsale_batch_control',cohort=True)
for label,mask in [('completed_first15',a.order.le(15)),('exclude_opening',a.order.ne(1)),('exclude_observed_endpoints',a.order.between(2,16)),('all_days_presence_proxy',a.all_days_observed)]:count_fit(a[mask],label)
count_fit(count_table(raw[~raw.duplicate_extra_candidate]),'dedup_candidates')
count_fit(a,'all_zones',outcome='allzone_count');count_fit(a,'levels_200_400',outcome='other_reserved_count')
for lo,hi in [(0,7),(7,14),(14,21),(21,28)]:
 g=window(lo,hi);aa=count_table(g,lo,hi);save(aa,f'activity_window_{lo}_{hi}.csv')
 if lo!=7:price_fit(g,f'window_{lo}_{hi}');count_fit(aa,f'window_{lo}_{hi}')
 gg=g[g.order.le(15)];bb=aa[aa.order.le(15)];assert bb.order.tolist()==list(range(1,16))
 price_fit(gg,f'fixed15_window_{lo}_{hi}');count_fit(bb,f'fixed15_window_{lo}_{hi}')
g28=window(0,28);a28=count_table(g28,0,28);a28=a28[a28.order.le(15)]
save(a28,'activity_fixed15_0_28.csv');count_fit(a28,'followup_fixed15_0_28');count_fit(a28,'followup_fixed15_0_28_allzone',outcome='allzone_count')
g07=window(0,7);a07=count_table(g07,0,7);count_fit(a07,'followup_last7_allzone',outcome='allzone_count')
for shift in [-1,1]:price_fit(window(shift=shift),f'start_shift_{shift:+d}h')
save(pd.DataFrame(prices),'price_models.csv');save(pd.DataFrame(counts),'activity_models.csv')
ix=pd.read_csv(P/'price_event_indices.csv');aa=pd.read_csv(P/'activity_main_events.csv')
merged=aa.merge(ix.drop(columns=['order']),on='event_date');save(merged,'Harry_event_summary.csv')
quality={f:int(raw.loc[raw.ordinary100_seat,f].sum()) for f in ['qty_unknown','duplicate_extra_candidate','price_extreme_review','price_above_10000_review']}
s=dict(accepted_rows=len(d),accepted_events=len(ev),primary_price=prices[0],primary_activity=counts[0],primary_quality=quality,primary_allzone_records=int(a.allzone_count.sum()),all_days_observed=int(a.all_days_observed.sum()),max_gap_range=[float(a.max_observed_gap_hours.min()),float(a.max_observed_gap_hours.max())],first6_index=float(merged.loc[merged.order.le(6),'adjusted_index'].mean()),last6_available_index=float(merged.tail(6).adjusted_index.mean()),first6_count=float(a.loc[a.order.le(6),'ordinary100_count'].mean()),last6_available_count=float(a.tail(6).ordinary100_count.mean()))
(P/'summary.json').write_text(json.dumps(s,indent=2));assert a.ordinary100_count.sum()==len(pd.read_csv(P/'price_main_records.csv'))
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':150})
fig,axes=plt.subplots(2,1,figsize=(11,8),sharex=True,layout='constrained')
axes[0].plot(ix.order,ix.adjusted_index,'o-',color='#246B83',label='Adjusted event price index');axes[0].plot(ix.order,ix.fitted_index,'--',color='#C47722',label='Linear order association');axes[0].axhline(100,color='#bbb',lw=.7)
axes[0].set(ylabel='Index (first 6 mean = 100)',title='Harry Styles / MSG / sh / numeric 100 Level / 7-14 days before show');axes[0].legend()
axes[1].bar(a.order,a.ordinary100_count,color='#246B83',alpha=.8,label='Observed records');axes[1].plot(aa.order,aa.fitted_count,'o--',color='#C47722',label='Weekday-adjusted fit');axes[1].set(ylabel='Records per 7-day window',xlabel='Official show order; #17 quarantined; later windows not yet complete');axes[1].legend(loc='upper left')
axes[1].set_xticks(ix.order);axes[1].set_xticklabels([f'{int(x)}\n{z[5:]}' for x,z in zip(ix.order,ix.event_date)],fontsize=8)
fig.savefig(F/'harry_main.png',bbox_inches='tight');plt.close(fig)
fig,axes=plt.subplots(1,2,figsize=(12,7),layout='constrained')
for ax,models,title in zip(axes,[prices,counts],['Adjusted prices','Observed activity']):
 q=pd.DataFrame(models).iloc[::-1];y=np.arange(len(q));ax.errorbar(q.pct_per_10,y,xerr=np.array([q.pct_per_10-q.ci_low_pct,q.ci_high_pct-q.pct_per_10]),fmt='o',capsize=3,color='#246B83');ax.axvline(0,color='#999',lw=.8);ax.set_yticks(y);ax.set_yticklabels(q.model,fontsize=7);ax.set(title=title,xlabel='% per 10 later shows; exploratory 95% CI')
fig.savefig(F/'harry_sensitivity.png',bbox_inches='tight');plt.close(fig)
print(json.dumps(s,indent=2));print(pd.DataFrame(prices)[['model','n_events','n_records','pct_per_10','ci_low_pct','ci_high_pct']].to_string(index=False));print(pd.DataFrame(counts)[['model','n_events','pct_per_10','ci_low_pct','ci_high_pct']].to_string(index=False))

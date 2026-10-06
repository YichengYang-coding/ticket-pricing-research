"""Independent raw lineage, weighted partial-regression and count profile checks."""
from pathlib import Path
import json,hashlib
import pandas as pd
import numpy as np
from scipy import linalg,optimize
R=Path(__file__).resolve().parent;P=R/'processed'
rawcols=['Date/Time (EDT)','Source','Zone','Section','Row','Qty','Price']
allr=pd.read_csv(P/'sales_cleaned_all_records.csv',dtype=str,keep_default_na=False)
manifest=pd.read_csv(P/'source_manifest.csv')
for e in manifest.itertuples():
 p=R/'raw'/e.source_file;assert hashlib.sha256(p.read_bytes()).hexdigest()==e.sha256
 assert pd.read_csv(p,dtype=str,keep_default_na=False).equals(allr[allr.source_file.eq(e.source_file)][rawcols].reset_index(drop=True))
assert len(allr)==39427 and allr.record_key.nunique()==39427
d=allr[allr.included_in_research.eq('True')];assert len(d)==37021 and d.event_date.nunique()==29
assert not d.event_date.eq('2026-10-02').any()
g=pd.read_csv(P/'price_main_records.csv');assert g.lead.gt(7).all() and g.lead.le(14).all()
joined=g.merge(d[['record_key','source']],on='record_key',validate='one_to_one');assert joined.source.eq('sh').all()
g['weekday']=pd.to_datetime(g.event_date).dt.day_name();g['lead_bucket']=np.ceil(g.lead).astype(int).astype(str)
Z=np.column_stack([np.ones(len(g)),pd.get_dummies(g[['section','row','qty_group','lead_bucket','weekday']].astype(str),drop_first=True,dtype=float).to_numpy()])
x=g.order.to_numpy()/10;y=np.log(g.price_usd_base.to_numpy());sw=np.sqrt(1/g.groupby('event_date').event_date.transform('size')).to_numpy()
Z*=sw[:,None];x*=sw;y*=sw
rx=x-Z@linalg.lstsq(Z,x)[0];ry=y-Z@linalg.lstsq(Z,y)[0];b=float(rx@ry/(rx@rx))
summary=json.loads((P/'summary.json').read_text());assert abs(b-summary['primary_price']['beta'])<1e-9
checks={};cm=pd.read_csv(P/'activity_models.csv').set_index('model')
for fname,label in [('activity_main_events.csv','primary_7_14'),('activity_window_0_7.csv','window_0_7'),('activity_fixed15_0_28.csv','followup_fixed15_0_28')]:
 a=pd.read_csv(P/fname);xx=a.order.to_numpy()/10;yy=a.ordinary100_count.to_numpy();group=a.weekday.to_numpy()
 def prof(b):
  val=0.
  for day in np.unique(group):
   sel=group==day;pred=np.exp(b*xx[sel]);mu=yy[sel].sum()*pred/pred.sum();val+=np.sum(mu-yy[sel]*np.log(mu))
  return val
 fit=optimize.minimize_scalar(prof,bounds=(-2,2),method='bounded',options={'xatol':1e-12})
 assert abs(fit.x-cm.loc[label,'beta'])<1e-6;checks[label]=fit.x
a=pd.read_csv(P/'activity_main_events.csv');assert a.exposure_days.eq(7).all();assert (a.set_index('event_date').ordinary100_count==g.groupby('event_date').size()).all()
for p in P.glob('window_eligibility_*.csv'):
 m=pd.read_csv(p);m=m[m.complete_window_proxy]
 assert (pd.to_datetime(m.window_end,utc=True)<=pd.to_datetime(m.conservative_cutoff,utc=True)).all()
 assert (pd.to_datetime(m.window_start,utc=True)>=pd.to_datetime(m.first_sh_record,utc=True)).all()
parts=[]
for lo,hi in [(0,7),(7,14),(14,21),(21,28)]:
 p=pd.read_csv(P/f'activity_window_{lo}_{hi}.csv');parts.append(p[p.order.le(15)].set_index('order')[['ordinary100_count','allzone_count']])
total=sum(parts);aggregate=pd.read_csv(P/'activity_fixed15_0_28.csv').set_index('order')[total.columns];assert total.equals(aggregate)
assert g.order.max()==18 and 17 not in g.order.unique()
result=dict(all_raw_bytes_and_seven_columns_preserved=True,accepted_rows=len(d),quarantine_rows=len(allr)-len(d),independent_price_beta_fwl=b,independent_count_beta_profile_likelihood=checks,complete_window_boundaries_verified=True,four_disjoint_windows_sum_to_28day_counts=True)
(P/'verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

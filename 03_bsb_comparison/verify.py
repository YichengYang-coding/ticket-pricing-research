"""Independent lineage, window and main coefficient checks."""
from pathlib import Path
import json,hashlib
import pandas as pd
import numpy as np
from scipy import linalg,optimize
R=Path(__file__).resolve().parent;P=R/'processed'
rawcols=['Date/Time (EDT)','Source','Zone','Section','Row','Qty','Price']
d=pd.read_csv(P/'sales_cleaned_all_records.csv',dtype=str,keep_default_na=False)
manifest=pd.read_csv(P/'event_manifest.csv')
for e in manifest.itertuples():
 b=(R/'raw'/e.source_file).read_bytes();assert hashlib.sha256(b).hexdigest()==e.sha256
 original=pd.read_csv(R/'raw'/e.source_file,dtype=str,keep_default_na=False)
 assert original.equals(d[d.source_file.eq(e.source_file)][rawcols].reset_index(drop=True))
assert len(d)==22154 and d.record_key.nunique()==22154
g=pd.read_csv(P/'price_main_records.csv');assert g.lead.gt(7).all() and g.lead.le(14).all()
joined=g.merge(d[['record_key','source']],on='record_key',validate='one_to_one');assert joined.source.eq('sh').all()
g['weekday']=pd.to_datetime(g.event_date).dt.day_name();g['lead_bucket']=np.ceil(g.lead).astype(int).astype(str)
Z=np.column_stack([np.ones(len(g)),pd.get_dummies(g[['section','row','qty_group','lead_bucket','weekday']].astype(str),drop_first=True,dtype=float).to_numpy()])
x=g.order.to_numpy()/10;y=np.log(g.price_usd_base.to_numpy());sw=np.sqrt(1/g.groupby('event_date').event_date.transform('size')).to_numpy()
Z*=sw[:,None];x*=sw;y*=sw
rx=x-Z@linalg.lstsq(Z,x)[0];ry=y-Z@linalg.lstsq(Z,y)[0];b=float(rx@ry/(rx@rx))
summary=json.loads((P/'summary.json').read_text());assert abs(b-summary['primary_price']['beta'])<1e-9
a=pd.read_csv(P/'activity_main_events.csv');counts=g.groupby('event_date').size()
assert (a.set_index('event_date').ordinary100_count==counts).all();assert a.exposure_days.eq(7).all()
xx=a.order.to_numpy()/10;yy=a.ordinary100_count.to_numpy();group=a.weekday.to_numpy()
def prof(b):
 val=0.
 for day in np.unique(group):
  sel=group==day;pred=np.exp(b*xx[sel]);mu=yy[sel].sum()*pred/pred.sum();val+=np.sum(mu-yy[sel]*np.log(mu))
 return val
q=optimize.minimize_scalar(prof,bounds=(-2,2),method='bounded',options={'xatol':1e-12})
assert abs(q.x-summary['primary_activity']['beta'])<1e-6
result={'raw_bytes_and_all_seven_columns_preserved':True,'rows':len(d),'events':len(manifest),'primary_rows':len(g),'price_beta_fwl':b,'count_beta_profile_likelihood':q.x,'lineage_and_primary_windows_pass':True}
(P/'verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

"""Preserve original exports; append auditable fields and flags. No network calls."""
from pathlib import Path
from datetime import timezone,timedelta
import hashlib,json,itertools
import pandas as pd
import numpy as np

R=Path(__file__).resolve().parent; P=R/'processed';P.mkdir(exist_ok=True)
RAW=['Date/Time (EDT)','Source','Zone','Section','Row','Qty','Price']
DATES=['07-16','07-17','07-18','07-23','07-24','07-25','07-30','07-31','08-01','08-06','08-07','08-08','08-13','08-14','08-15','08-20','08-21','08-22','08-27','08-28','08-29']
def save(d,name):d.to_csv(P/name,index=False,encoding='utf-8-sig')
def bins(h):
 return pd.Series(np.select([h.isna(),h.le(0),h.le(12),h.le(24),h.le(48),h.le(96),h.le(168)],['invalid_time','at_or_after_start','within12h','12to24h','24to48h','48to96h','4to7d'],default='over7d'),index=h.index)
def run():
 frames=[];meta=[]
 for order,dt in enumerate(DATES,1):
  name='BB'+str(int(dt[:2]))+dt[3:]+'.csv';p=R/'raw'/name
  g=pd.read_csv(p,dtype=str,keep_default_na=False);assert list(g)==RAW
  digest=hashlib.sha256(p.read_bytes()).hexdigest()
  g['source_file']=name;g['source_row']=np.arange(len(g))+2;g['source_sha256']=digest
  g['record_key']=name+':'+g.source_row.astype(str);g['event_date']='2026-'+dt;g['order']=order
  g['event_identity_status']='filename_plus_official_schedule_no_event_id_in_export'
  start=pd.Timestamp('2026-'+dt+' 20:00',tz='America/Los_Angeles')
  g['event_start_local']=str(start);g['event_start_utc']=str(start.tz_convert('UTC'))
  t=pd.to_datetime(g[RAW[0]],format='%m-%d-%y / %I:%M %p',errors='coerce').dt.tz_localize(timezone(timedelta(hours=-4)))
  g['observed_at_utc']=t.dt.tz_convert('UTC');g['observed_at_pacific']=t.dt.tz_convert('America/Los_Angeles')
  g['winter_timezone_header_ambiguity']=t.dt.month.lt(3)|(t.dt.month.eq(3)&t.dt.day.lt(8))
  g['hours_to_event_exact']=(start-g.observed_at_utc).dt.total_seconds()/3600
  g['days_to_event_exact']=g.hours_to_event_exact/24;g['time_bin']=bins(g.hours_to_event_exact)
  for raw,new in [('Source','source'),('Zone','zone'),('Section','section'),('Row','row')]:g[new]=g[raw].str.strip()
  g['source']=g.source.str.lower();g['zone']=g.zone.str.replace(r'(?i)^([1-4]00) level$',r'\1 Level',regex=True)
  for raw,new in [('Qty','qty'),('Price','price_usd_base'),('Section','section_num'),('Row','row_num')]:g[new]=pd.to_numeric(g[raw],errors='coerce')
  g['qty_unknown']=g.qty.eq(0);g['qty_invalid']=g.qty.isna()|g.qty.lt(0)|g.qty.mod(1).ne(0)
  g['qty_known']=g.qty.where(~g.qty_unknown&~g.qty_invalid)
  g['qty_group']=np.select([g.qty_invalid,g.qty_unknown,g.qty.eq(1),g.qty.eq(2),g.qty.eq(3),g.qty.eq(4)],['invalid','unknown','1','2','3','4'],default='5plus')
  g['price_invalid']=g.price_usd_base.isna()|~np.isfinite(g.price_usd_base)|g.price_usd_base.le(0)
  g['time_invalid']=t.isna();g['at_or_after_start']=g.hours_to_event_exact.le(0)
  g['zone_missing']=g.zone.eq('');g['row_missing']=g.row.str.upper().isin(['','N/A','NA','NULL'])
  g['numeric_seat']=g.row_num.notna()&g.row_num.mod(1).eq(0)&g.section_num.notna()
  g['ordinary100_seat']=g.zone.eq('100 Level')&g.section_num.between(101,110)&g.row_num.between(12,37)&g.numeric_seat
  g['other_reserved_seat']=g.zone.isin(['200 Level','300 Level','400 Level'])&g.numeric_seat&g.row_num.gt(0)
  g['valid_prestart']=~g.price_invalid&~g.time_invalid&~g.at_or_after_start&~g.qty_invalid
  g['eligible_100']=g.ordinary100_seat&g.valid_prestart
  g['duplicate_candidate']=g.duplicated(RAW,keep=False);g['duplicate_extra_candidate']=g.duplicated(RAW,keep='first')
  g['price_above_10000_review']=g.price_usd_base.gt(10000)
  frames.append(g)
  meta.append(dict(event_date='2026-'+dt,order=order,source_file=name,sha256=digest,rows=len(g),first_record_utc=str(g.observed_at_utc.min()),last_record_utc=str(g.observed_at_utc.max()),event_start_local=str(start),weekday=start.day_name(),announcement_cohort=('A_first6' if order<=6 else 'B_next6' if order<=12 else 'C_next3' if order<=15 else 'D_next3' if order<=18 else 'E_final3'),event_identity='filename_matches_schedule_no_exported_event_id',start_time_status='20:00_Pacific_listing_supported_common_time_assumption'))
 d=pd.concat(frames,ignore_index=True);m=pd.DataFrame(meta)
 d['identical_file_candidate']=d.source_sha256.isin(m.loc[m.sha256.duplicated(False),'sha256'])
 d['cross_event_exact_row_candidate']=d.groupby(RAW,dropna=False).source_file.transform('nunique').gt(1)
 sets={f:set(map(tuple,g[RAW].values)) for f,g in d.groupby('source_file')};overlap=[]
 for a,b in itertools.combinations(sorted(sets),2):
  n=len(sets[a]&sets[b])
  if n:overlap.append(dict(file_a=a,file_b=b,shared_exact_rows=n))
 save(pd.DataFrame(overlap,columns=['file_a','file_b','shared_exact_rows']),'cross_file_overlap.csv')
 logs=np.log(d.price_usd_base.where(~d.price_invalid));keys=[d.zone,d.source]
 median=logs.groupby(keys).transform('median');mad=(logs-median).abs().groupby(keys).transform('median')
 d['price_extreme_review']=((logs-median).abs()/(1.4826*mad.replace(0,np.nan))).gt(5)
 save(d,'sales_cleaned_all_records.csv');save(m,'event_manifest.csv')
 flags=['time_invalid','price_invalid','qty_invalid','qty_unknown','at_or_after_start','zone_missing','row_missing','duplicate_candidate','duplicate_extra_candidate','identical_file_candidate','cross_event_exact_row_candidate','price_above_10000_review','price_extreme_review','winter_timezone_header_ambiguity']
 audit=[]
 for label,g in [('all',d)]+list(d.groupby('source_file')):
  a=dict(scope=label,n_rows=len(g),ordinary100_seat=int(g.ordinary100_seat.sum()),eligible_100=int(g.eligible_100.sum()))
  a.update({c:int(g[c].sum()) for c in flags});a.update({'missing_'+c:int(g[c].eq('').sum()) for c in RAW})
  audit.append(a)
 save(pd.DataFrame(audit),'quality_audit.csv')
 save(d[d[flags[:3]+['at_or_after_start','zone_missing','row_missing','duplicate_candidate','cross_event_exact_row_candidate','price_above_10000_review','price_extreme_review']].any(axis=1)],'flagged_records.csv')
 save(d[d.duplicate_candidate],'duplicate_candidates.csv')
 save(d.groupby(['zone','source'],dropna=False).agg(n_records=('record_key','size'),first_utc=('observed_at_utc','min'),last_utc=('observed_at_utc','max')).reset_index(),'zone_source_summary.csv')
 save(d[d.valid_prestart].groupby(['event_date','source','zone','time_bin'],dropna=False).agg(n_records=('record_key','size'),median_base_price=('price_usd_base','median'),known_quantity_sum=('qty_known','sum'),qty_unknown=('qty_unknown','sum')).reset_index(),'lead_time_summary.csv')
 assert d.record_key.is_unique and len(d)==22154 and len(m)==21
 assert m.sha256.is_unique
 assert bins(pd.Series([0,0.01,12,12.001,24,48,96,168,169])).tolist()==['at_or_after_start','within12h','within12h','12to24h','12to24h','24to48h','48to96h','4to7d','over7d']
 assert d.loc[d.qty_unknown,'qty_known'].isna().all()
 for file,g in d.groupby('source_file'):
  original=pd.read_csv(R/'raw'/file,dtype=str,keep_default_na=False)
  assert original.equals(g[RAW].reset_index(drop=True))
 print(json.dumps(audit[0],ensure_ascii=False,indent=2))
if __name__=='__main__':run()

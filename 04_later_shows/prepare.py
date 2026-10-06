"""Reaudit preserved exports and harmonize only derived analysis fields."""
from pathlib import Path
import hashlib,json
import pandas as pd
import numpy as np
R=Path(__file__).resolve().parent;P=R/'processed';P.mkdir(exist_ok=True)
rawcols=['Date/Time (EDT)','Source','Zone','Section','Row','Qty','Price']
f=pd.read_csv(R/'upstream/sales_enriched_all_files.csv',keep_default_na=False,low_memory=False)
original=pd.read_csv(R/'upstream/sales_enriched_all_files.csv',dtype=str,keep_default_na=False)
# Force original seven fields back to literal strings, including empty/NA-like cells.
f[rawcols]=original[rawcols]
manifest=pd.read_csv(R/'upstream/event_manifest.csv',keep_default_na=False)
for e in manifest.itertuples():
 p=R/'raw'/e.source_file;assert hashlib.sha256(p.read_bytes()).hexdigest()==e.sha256
 assert pd.read_csv(p,dtype=str,keep_default_na=False).equals(f.loc[f.source_file.eq(e.source_file),rawcols].reset_index(drop=True))
f['qty_group_previous']=f.qty_group
qn=pd.to_numeric(f.qty_numeric,errors='coerce')
f['qty_group']=np.select([f.qty_unknown,qn.eq(1),qn.eq(2),qn.eq(3),qn.eq(4),qn.ge(5)],['unknown','1','2','3','4','5plus'],default='invalid')
for field in ['row_numeric','section_numeric','price_usd_base','days_to_event_exact','hours_to_event']:
 f[field]=pd.to_numeric(f[field],errors='coerce')
f['row_num']=f.row_numeric
f['valid_prestart']=f.eligible_price_prestart
f['ordinary100_seat']=f.eligible_100_common_seats
f['other_reserved_seat']=f.valid_prestart & ((f.zone.eq('200 Level')&f.section_numeric.between(201,227)&f.row_numeric.between(1,25)) | (f.zone.eq('400 Level')&f.section_numeric.between(413,420)&f.row_numeric.between(1,7)))
dates='08-26 08-28 08-29 09-02 09-04 09-05 09-09 09-11 09-12 09-16 09-18 09-19 09-23 09-25 09-26 09-30 10-02 10-03 10-07 10-09 10-10 10-14 10-16 10-17 10-21 10-23 10-24 10-28 10-30 10-31'.split()
order={'2026-'+dt:i+1 for i,dt in enumerate(dates)};f['order']=f.event_date.map(order)
f['event_start_utc']=pd.to_datetime(f.event_start_local,utc=True)
for c in rawcols:f['missing_'+c]=f[c].str.strip().str.upper().isin(['','NA','N/A','NAN','NULL','NONE'])
# Recompute time differences without rounding; confirm earlier correct <=12h bins.
hours=(f.event_start_utc-pd.to_datetime(f.observed_at_utc,utc=True)).dt.total_seconds()/3600
assert np.allclose(hours,f.hours_to_event)
def bins(h):
 return np.select([h.le(0),h.le(12),h.le(24),h.le(48),h.le(96),h.le(168)],['at_or_after_start','within12h','12to24h','24to48h','48to96h','4to7d'],default='gt7d')
assert np.array_equal(bins(hours),f.time_bin)
assert list(bins(pd.Series([0,12,24,48,96,168,169])))==['at_or_after_start','within12h','12to24h','24to48h','48to96h','4to7d','gt7d']
def save(g,n):g.to_csv(P/n,index=False,encoding='utf-8-sig')
save(f,'sales_cleaned_all_records.csv');d=f[f.included_in_research].copy();save(d,'research_accepted_records.csv')
save(f[~f.included_in_research],'quarantined_records.csv');save(manifest,'source_manifest.csv')
flags=['qty_unknown','qty_invalid','qty_large_review','price_invalid','time_invalid','at_or_after_start','source_unknown','row100_missing','row100_review','section100_review','section100_wc_label','duplicate_candidate','duplicate_extra_candidate','cross_source_candidate','price_extreme_review','price_above_10000_review','winter_timezone_ambiguous']+['missing_'+x for x in rawcols]
audit=[]
for scope,g in [('all_active_exports',f),('accepted',d)]:
 audit.extend([dict(scope=scope,check=c,count=int(g[c].sum())) for c in flags])
save(pd.DataFrame(audit),'quality_audit.csv')
save(f[f[flags].any(axis=1)],'flagged_records.csv')
save(d.groupby(['event_date','source','zone']).size().rename('records').reset_index(),'seat_source_counts.csv')
save(d.groupby(['event_date','source','time_bin']).agg(records=('record_key','size'),median_price=('price_usd_base','median')).reset_index(),'lead_time_summary.csv')
out={'all_rows':len(f),'accepted_rows':len(d),'accepted_events':d.event_date.nunique(),'quarantined_rows':int((~f.included_in_research).sum()),'original_columns_preserved':True,'raw_sha256_verified':True,'ordinary100_records':int(d.ordinary100_seat.sum()),'other_reserved_records':int(d.other_reserved_seat.sum())}
(P/'cleaning_summary.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))

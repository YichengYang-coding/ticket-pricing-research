from pathlib import Path
from datetime import timezone,timedelta,datetime
from collections import Counter
import os,json,hashlib,shutil,ast
import numpy as np
import pandas as pd
from scipy.linalg import solve

ROOT=Path(__file__).resolve().parent;O=ROOT/'outputs';R=ROOT/'raw'
BASE=ROOT/'input/Harry_cleaned_sales_previous.csv'
if not BASE.exists():BASE=ROOT.parent/'msg_seat_study/data/Harry_cleaned_sales.csv'
V1=ROOT/'model_v1_frozen.py'
if not V1.exists():V1=ROOT.parent/'msg_price_model/model_v1.py'
OLDCOEF=ROOT/'input/previous_coefficients.csv'
if not OLDCOEF.exists():OLDCOEF=ROOT.parent/'msg_price_model/outputs/final_coefficients.csv'
UPLOAD=ROOT.parent/'upload'
FILES=[('01-1002.csv','2026-10-02','14-1002.csv'),('02-1007.csv','2026-10-07','12-1007.csv'),('03-1003.csv','2026-10-03','13-1003.csv'),('04-0930.csv','2026-09-30','sales_data.csv')]
C=['Date/Time (EDT)','Source','Zone','Section','Row','Qty','Price']
RECEIVED=pd.Timestamp('2026-09-29T22:36:39Z')
ORIGIN=RECEIVED
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(df,name):
    p=O/name;t=p.with_suffix(p.suffix+'.pending');df.to_csv(t,index=False);os.replace(t,p)
def js(obj,name):
    p=O/name;t=p.with_suffix(p.suffix+'.pending');t.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(t,p)
def norm(frame):
    f=frame[C].fillna('').astype(str).copy()
    for col in C:f[col]=f[col].str.strip()
    for col in ['Qty','Price']:f[col]=pd.to_numeric(f[col],errors='coerce').map(lambda v:format(v,'.12g'))
    return f
def keys(frame):return list(map(tuple,norm(frame).to_numpy()))
def qgroup(q):
    return np.select([q.eq(0),q.eq(1),q.eq(2),q.eq(3),q.eq(4),q.ge(5)],['unknown','1','2','3','4','5plus'],default='invalid')

old=pd.read_csv(BASE,low_memory=False);oldstr=pd.read_csv(BASE,dtype=str,keep_default_na=False);old[C]=oldstr[C]
raw_new=[];reconciliations=[];changes=[];unmatched_old=[];novel=[];man=[];quality=[]
for fn,event,priorfn in FILES:
    src=R/fn
    if not src.exists():shutil.copyfile(UPLOAD/fn,src)
    f=pd.read_csv(src,dtype=str,keep_default_na=False);assert list(f.columns)==C
    prev=old[old.source_file.eq(priorfn)].copy();newnorm=norm(f);oldnorm=norm(prev)
    newkeys=list(map(tuple,newnorm.to_numpy()));oldkeys=list(map(tuple,oldnorm.to_numpy()))
    nc,oc=Counter(newkeys),Counter(oldkeys);matches=sum((nc&oc).values())
    extras=list((nc-oc).elements());missing=list((oc-nc).elements())
    revision_new=set();revision_old=set()
    for i,a in enumerate(missing):
        hits=[(j,b) for j,b in enumerate(extras) if a[:5]==b[:5]]
        oldhits=[aa for aa in missing if aa[:5]==a[:5]]
        if len(hits)==1 and len(oldhits)==1:
            j,b=hits[0];revision_new.add(j);revision_old.add(i)
            changes.append({'event_date':event,'old_file':priorfn,'new_file':fn,**{k:a[t] for t,k in enumerate(C[:5])},'old_qty':a[5],'new_qty':b[5],'old_price':a[6],'new_price':b[6],'interpretation':'same timestamp/source/seat signature; likely field revision, no listing ID'})
    for i,k in enumerate(missing):
        if i not in revision_old:unmatched_old.append({'event_date':event,'old_file':priorfn,**dict(zip(C,k)),'status':'not present in latest snapshot; retained in prior raw; reason unknown'})
    prevmax=pd.to_datetime(prev.observed_at_utc,utc=True).max()
    pure_new=[b for j,b in enumerate(extras) if j not in revision_new]
    pure_dt=pd.to_datetime(pd.Series([x[0] for x in pure_new],dtype=str),format='%m-%d-%y / %I:%M %p',errors='coerce').dt.tz_localize(timezone(timedelta(hours=-4))).dt.tz_convert('UTC')
    recon={'event_date':event,'new_file':fn,'old_file':priorfn,'prior_accepted':bool(prev.included_in_research.iloc[0]),'old_rows':len(prev),'new_rows':len(f),'exact_overlap_records':matches,'unmatched_new':len(extras),'likely_revisions':len(revision_new),'new_distinct_records':len(pure_new),'new_after_prior_last_timestamp':int(pure_dt.gt(prevmax).sum()),'backfilled_or_at_prior_last_timestamp':int(pure_dt.le(prevmax).sum()),'old_unmatched_unresolved':len(missing)-len(revision_old),'net_snapshot_change':len(f)-len(prev),'prior_last_record_utc':str(prevmax)}
    reconciliations.append(recon)
    for k in pure_new:novel.append({'event_date':event,'new_file':fn,**dict(zip(C,k))})
    z=f.copy();z['event_date']=event;z['event_key']='HS_MSG_'+event;z['source_file']='update_20260929/'+fn;z['source_row_number']=np.arange(2,len(z)+2);z['record_key']=z.source_file+':'+z.source_row_number.astype(str);z['source_file_sha256']=sha(src)
    ts0=pd.to_datetime(z[C[0]],format='%m-%d-%y / %I:%M %p',errors='coerce')
    edt=ts0.dt.tz_localize(timezone(timedelta(hours=-4)));ts=edt.dt.tz_convert('UTC');alt=ts0.dt.tz_localize('America/New_York',ambiguous='NaT',nonexistent='NaT')
    z['observed_at_edt']=edt.astype(str);z['observed_at_utc']=ts.astype(str);z['observed_at_eastern_alternative']=alt.astype(str);z['winter_timezone_ambiguous']=ts.notna()&alt.notna()&ts.ne(alt.dt.tz_convert('UTC'))
    start=pd.Timestamp(event+' 20:00',tz='America/New_York');z['event_start_local']=str(start);z['event_start_utc']=str(start.tz_convert('UTC'))
    h=(start.tz_convert('UTC')-ts).dt.total_seconds()/3600;z['hours_to_event']=h;z['days_to_event_exact']=h/24;z['calendar_days_to_event']=(pd.Timestamp(event)-ts0.dt.normalize()).dt.days
    z['time_bin']=np.select([h.le(0),h.le(12),h.le(24),h.le(48),h.le(96),h.le(168)],['at_or_after_start','within12h','12to24h','24to48h','48to96h','4to7d'],default='gt7d')
    for a,b in [('Source','source'),('Zone','zone'),('Section','section'),('Row','row')]:z[b]=z[a].str.strip()
    z['source']=z.source.str.lower();p=pd.to_numeric(z.Price,errors='coerce');q=pd.to_numeric(z.Qty,errors='coerce');rr=pd.to_numeric(z.Row,errors='coerce');ss=pd.to_numeric(z.Section,errors='coerce')
    z['price_usd_base']=p;z['qty_numeric']=q;z['row_numeric']=rr;z['row_num']=rr;z['section_numeric']=ss
    z['qty_unknown']=q.eq(0);z['qty_invalid']=q.isna()|q.lt(0)|q.ne(q.round());z['qty_large_review']=q.gt(20);z['qty_known']=q.where(q.gt(0));z['qty_group']=qgroup(q)
    z['price_invalid']=p.isna()|~np.isfinite(p)|p.le(0);z['time_invalid']=ts.isna();z['at_or_after_start']=h.le(0);z['source_unknown']=~z.source.isin(['sh','vs'])
    zone100=z.zone.eq('100 Level');exactsec=z.Section.str.fullmatch(r'10[1-9]|11[0-9]|120');rvalid=rr.between(1,22)&rr.eq(rr.round())
    z['row100_missing']=zone100&z.Row.str.strip().eq('');z['row100_review']=zone100&~rvalid;z['section100_review']=zone100&~exactsec;z['section100_wc_label']=zone100&z.Section.str.contains('WC',case=False)
    z['duplicate_candidate']=newnorm.duplicated(keep=False);z['duplicate_extra_candidate']=newnorm.duplicated();z['cross_source_candidate']=newnorm.drop(columns='Source').duplicated(keep=False)
    z['price_above_10000_review']=p.gt(10000)
    logp=np.log(p.where(p.gt(0)));kk=z.source+'|'+z.zone;med=logp.groupby(kk).transform('median');mad=(logp-med).abs().groupby(kk).transform('median');ng=logp.groupby(kk).transform('count')
    z['price_extreme_review']=ng.ge(20)&mad.gt(0)&((logp-med).abs()/(1.4826*mad)).gt(4.5)
    z['eligible_price_prestart']=~z.price_invalid&~z.time_invalid&~z.qty_invalid&h.gt(0);z['valid_prestart']=z.eligible_price_prestart
    z['eligible_100_common_seats']=z.valid_prestart&exactsec&rvalid;z['ordinary100_seat']=z.eligible_100_common_seats;z['eligible_100_main_30d']=z.ordinary100_seat&h.le(720)
    z['other_reserved_seat']=z.valid_prestart&((z.zone.eq('200 Level')&ss.between(201,227)&rr.between(1,25))|(z.zone.eq('400 Level')&ss.between(413,420)&rr.between(1,7)))
    z['official_face_value_usd']=np.nan;z['official_face_value_status']='not_verified';z['upload_batch']='20260929_update';z['identity_status']='user_filename_plus_historical_fingerprint';z['included_in_research']=True;z['event_id_in_export']=False;z['identical_content_different_event_candidate']=False
    z['content_key']=[hashlib.sha256(json.dumps(k,ensure_ascii=False).encode()).hexdigest() for k in newkeys]
    z['observed_calendar_week']=ts0.dt.strftime('%Y-%W');z['received_at_utc']=str(RECEIVED);z['snapshot_status']='latest_for_event';z['cleaning_version']='update_20260929';z['known_export_time_utc']='not_provided'
    for col in C:z['missing_'+col]=z[col].str.strip().str.upper().isin(['','NA','N/A','NAN','NULL','NONE'])
    # Preserve the seven raw field values exactly, including empty strings.
    assert z[C].equals(f[C]);raw_new.append(z)
    man.append({'event_date':event,'original_upload_name':fn.split('-',1)[1],'preserved_file':fn,'sha256':sha(src),'bytes':src.stat().st_size,'records':len(z),'earliest_record_utc':str(ts.min()),'latest_record_utc':str(ts.max()),'received_at_utc':str(RECEIVED),'exact_download_timestamp':'not supplied'})
    flags=['qty_unknown','qty_invalid','qty_large_review','price_invalid','time_invalid','at_or_after_start','source_unknown','row100_missing','row100_review','section100_review','section100_wc_label','duplicate_candidate','duplicate_extra_candidate','price_extreme_review','price_above_10000_review','winter_timezone_ambiguous']+['missing_'+x for x in C]
    quality.extend([{'event_date':event,'check':flag,'count':int(z[flag].sum())} for flag in flags])

new=pd.concat(raw_new,ignore_index=True)
events_replaced=[x[1] for x in FILES]
unchanged=old[old.included_in_research&~old.event_date.isin(events_replaced)].copy();unchanged['snapshot_status']='prior_retained'
current=pd.concat([unchanged,new],ignore_index=True)
dates='08-26 08-28 08-29 09-02 09-04 09-05 09-09 09-11 09-12 09-16 09-18 09-19 09-23 09-25 09-26 09-30 10-02 10-03 10-07 10-09 10-10 10-14 10-16 10-17 10-21 10-23 10-24 10-28 10-30 10-31'.split();order={'2026-'+dt:i+1 for i,dt in enumerate(dates)};current['order']=current.event_date.map(order)
assert current.event_date.nunique()==30
assert len(current)==38570
save(new,'new_files_cleaned.csv');save(current,'Harry_current_sales_20260929.csv');save(pd.DataFrame(man),'source_manifest.csv');save(pd.DataFrame(reconciliations),'reconciliation.csv');save(pd.DataFrame(changes),'likely_field_revisions.csv');save(pd.DataFrame(unmatched_old),'prior_rows_absent_latest.csv');save(pd.DataFrame(novel),'new_distinct_records_vs_prior.csv');save(pd.DataFrame(quality),'new_file_quality_counts.csv')
save(new[new[[c for c in new.columns if c.startswith('missing_')]+['qty_unknown','row100_review','section100_review','price_extreme_review','duplicate_candidate']].any(axis=1)],'new_flagged_records.csv')

def universe(f):
    m=f[f.included_in_research&f.source.eq('sh')&f.Section.astype(str).str.fullmatch(r'10[1-9]|11[0-9]|120')&f.valid_prestart&f.price_usd_base.gt(0)].copy()
    m['r']=pd.to_numeric(m.Row,errors='coerce');m=m[m.r.between(3,22)&m.r.eq(m.r.round())].copy();m['r']=m.r.astype(int);m['s']=pd.to_numeric(m.Section).astype(int);m['ts']=pd.to_datetime(m.observed_at_utc,utc=True);m['event_start']=pd.to_datetime(m.event_start_utc,utc=True);m['event']=m.event_date.astype(str);m['q']=m.qty_group.astype(str);m['price']=m.price_usd_base.astype(float);m['band']=pd.cut(m.r,[2,6,10,15,22],labels=['3-6','7-10','11-15','16-22']).astype(str)
    return m.sort_values(['ts','record_key']).reset_index(drop=True)
old_u=universe(old);u=universe(current)
node=ast.parse(V1.read_text());functions=[n for n in node.body if isinstance(n,ast.FunctionDef) and n.name in ['design','fit','baselines','summarize']]
ns={'pd':pd,'np':np,'solve':solve,'sections':list(range(101,121)),'quantities':['unknown','1','2','3','4','5plus'],'events':sorted(old_u.event.unique())}
exec(compile(ast.Module(body=functions,type_ignores=[]),str(V1),'exec'),ns)
previous_origin=pd.Timestamp('2026-09-28T22:00:00Z');old_coef=pd.read_csv(OLDCOEF).set_index('term').coefficient
new_u=universe(new)
post=new_u[new_u.ts.ge(previous_origin)&new_u.event.isin(old_u.event.unique())].copy()
X,cols,pen=ns['design'](post,previous_origin);assert list(old_coef.index)==cols
post['previous_frozen_model_price']=np.exp(X@old_coef.to_numpy())
save(post[['record_key','event','ts','s','r','q','price','previous_frozen_model_price']],'previous_model_additional_period_check.csv')
old_check=[]
for event,g in post.groupby('event'):
    e=g.previous_frozen_model_price-g.price
    old_check.append({'event_date':event,'n':len(g),'mae_usd':float(abs(e).mean()),'median_ape_pct':float(100*(abs(e)/g.price).median()),'median_signed_pct':float(100*(e/g.price).median()),'status':'additional retrospective period, not post-publication prospective validation'})
save(pd.DataFrame(old_check),'previous_model_additional_period_metrics.csv')

ns['events']=sorted(u.event.unique())
train=u[u.ts.lt(ORIGIN)&u.ts.ge(ORIGIN-pd.Timedelta(days=90))].copy()
coef,names,it=ns['fit'](train,ORIGIN)
save(pd.DataFrame({'term':names,'coefficient':coef}),'updated_coefficients.csv')
grids=[]
for label,target in [('snapshot',ORIGIN),('next_day_18NY',pd.Timestamp('2026-09-30 18:00',tz='America/New_York').tz_convert('UTC'))]:
    for event in sorted(events_replaced):
        for s in range(101,121):
            for row in [6,10,15,20]:
                grids.append({'forecast':label,'event':event,'s':s,'r':row,'q':'2','ts':target,'event_start':pd.Timestamp(event+' 20:00',tz='America/New_York').tz_convert('UTC'),'band':'3-6' if row<=6 else '7-10' if row<=10 else '11-15' if row<=15 else '16-22'})
grid=pd.DataFrame(grids);X,_,_=ns['design'](grid,ORIGIN);grid['model_price_usd_base']=np.exp(X@coef)
grid=pd.concat([grid,ns['baselines'](train,grid,ORIGIN)],axis=1)
recent=train[train.ts.ge(ORIGIN-pd.Timedelta(hours=72))]
cnt=recent.groupby(['event','s','band']).size()
cntq=recent.groupby(['event','s','band','q']).size()
grid['comparable_n72_any_quantity']=[int(cnt.get((x.event,x.s,x.band),0)) for x in grid.itertuples()]
grid['comparable_n72_same_quantity']=[int(cntq.get((x.event,x.s,x.band,x.q),0)) for x in grid.itertuples()]
grid['data_origin_utc']=str(ORIGIN);grid['source']='sh';grid['quote_status']='model estimate, no executable listing or fee information'
save(grid,'forecast_grid_4_events.csv');save(grid[grid.s.eq(107)&grid.r.eq(15)],'reference_seat_107_row15.csv')
eventstat=[]
for event,g in new.groupby('event_date'):
    uu=new_u[new_u.event.eq(event)];last=pd.to_datetime(g.observed_at_utc,utc=True).max()
    eventstat.append({'event_date':event,'raw_rows':len(g),'ordinary100_sh_model_rows':len(uu),'new_model_rows_after_previous_origin':int(uu.ts.ge(previous_origin).sum()),'last_record_utc':str(last),'hours_since_last_record_at_origin':float((ORIGIN-last).total_seconds()/3600),'last_72h_model_records':int(uu.ts.ge(ORIGIN-pd.Timedelta(hours=72)).sum())})
save(pd.DataFrame(eventstat),'event_update_summary.csv')
generated=pd.Timestamp.now(tz='UTC')
audit={'previous_input_sha256':sha(BASE),'previous_input_rows':len(old),'previous_accepted_rows':int(old.included_in_research.sum()),'new_files_rows':len(new),'updated_accepted_rows':len(current),'updated_events':current.event_date.nunique(),'new_model_universe_rows':len(u),'model_training_rows_90d':len(train),'model_training_events':train.event.nunique(),'model_iterations':it,'data_origin_utc':str(ORIGIN),'generated_at_utc':str(generated),'latest_new_record_utc':str(pd.to_datetime(new.observed_at_utc,utc=True).max()),'model_v1_source_sha256':sha(V1),'previous_coefficients_sha256':sha(OLDCOEF),'old_model_additional_check_rows':len(post),'qty_revision_candidates':len(changes),'unresolved_old_rows_absent_latest':len(unmatched_old),'raw_original_fields_preserved':True,'event_id_present_in_exports':False,'old_model_check_is_prospective':False,'forecast_evaluation_start_utc':'2026-09-30 04:00:00+00:00','forecast_evaluation_end_utc':'2026-10-01 04:00:00+00:00','forecast_evaluation_note':'Use fixed coefficients and recorded time; only valid pre-start sh Row3-22 sales. Do not refit before scoring.'}
js(audit,'audit.json')
js({'origin_utc':str(ORIGIN),'generated_at_utc':str(generated),'events':ns['events'],'sections':ns['sections'],'quantities':ns['quantities'],'coefficients':dict(zip(names,map(float,coef))),'v1_source_sha256':sha(V1),'forecast_window':['2026-09-30T04:00:00Z','2026-10-01T04:00:00Z']},'frozen_forecast_model.json')
assert current.record_key.is_unique
assert len(pd.read_csv(O/'Harry_current_sales_20260929.csv',low_memory=False))==38570
assert train.ts.max()<ORIGIN
assert grid.model_price_usd_base.gt(0).all() and np.isfinite(grid.model_price_usd_base).all()
assert (pd.to_datetime(grid.event_start,utc=True)>pd.to_datetime(grid.ts,utc=True)).all()
for fn,ev,pf in FILES:
    saved=pd.read_csv(O/'new_files_cleaned.csv',dtype=str,keep_default_na=False);saved=saved[saved.source_file.eq('update_20260929/'+fn)]
    inp=pd.read_csv(R/fn,dtype=str,keep_default_na=False);assert saved[C].reset_index(drop=True).equals(inp[C])
print(json.dumps(audit,indent=2,ensure_ascii=False));print(pd.DataFrame(reconciliations).to_string(index=False));print(pd.DataFrame(old_check).round(2).to_string(index=False));print(grid[grid.s.eq(107)&grid.r.eq(15)][['forecast','event','model_price_usd_base','comparable_n72_any_quantity']].round(2).to_string(index=False));print(pd.DataFrame(quality).pivot(index='check',columns='event_date',values='count').to_string())

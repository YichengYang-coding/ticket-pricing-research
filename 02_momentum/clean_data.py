"""Extend the original audit, preserving original exports and disputed identities."""
from pathlib import Path
import hashlib, json, shutil
import numpy as np
import pandas as pd
import cleaning_v1_reference as base

ROOT=Path(__file__).resolve().parent
UPLOAD=ROOT/'raw'
NEW={p.name:p.stem.split('-')[1] for p in sorted(UPLOAD.glob('[0-9][0-9]-*.csv'))}
OLD={v+'.csv':k for k,v in base.MAPPING.items()}
QUARANTINE={'14-1002.csv','15-0930.csv'}

def run(input_dir=None):
    global UPLOAD,NEW
    if input_dir is not None:UPLOAD=Path(input_dir).resolve()
    NEW={p.name:p.stem.split('-')[1] for p in sorted(UPLOAD.glob('[0-9][0-9]-*.csv'))}
    for d in ['raw','raw/quarantine','processed','figures']:(ROOT/d).mkdir(parents=True,exist_ok=True)
    frames=[]; manifests=[]
    # Use the previous implementation's complete field/flag logic one file at a time.
    # The original, previously identified Sep30 export is a separate older snapshot.
    selected={**OLD,**NEW,'sales_data.csv':'0930'}
    originalmap=base.MAPPING.copy();base.ROOT=ROOT
    for filename,mmdd in selected.items():
        # Each call selects only one file, so disputed cross-file equality is audited below.
        base.MAPPING={mmdd:Path(filename).stem}
        f=base.load_data(UPLOAD)
        f['upload_batch']= 'new_20260928' if filename in NEW else ('previous_sep30_snapshot' if filename=='sales_data.csv' else 'completed_shows_v1')
        f['identity_status']='quarantined_identical_files_different_event_dates' if filename in QUARANTINE else 'filename_mapping_previously_or_currently_user_supplied'
        f['included_in_research']=filename not in QUARANTINE
        f['event_id_in_export']=False
        m=pd.read_csv(ROOT/'processed/event_manifest.csv',keep_default_na=False)
        m['included_in_research']=filename not in QUARANTINE
        m['identity_status']=f.identity_status.iloc[0]
        m['last_record_time']=str(f.observed_at_edt.max())
        m['first_record_time']=str(f.observed_at_edt.min())
        m['100_level_rows']=int(f.zone.eq('100 Level').sum())
        m['upload_batch']=f.upload_batch.iloc[0]
        m['export_time']='not_in_csv'
        manifests.append(m);frames.append(f)
        if filename in QUARANTINE:shutil.copyfile(UPLOAD/filename,ROOT/'raw/quarantine'/filename)
    base.MAPPING=originalmap
    f=pd.concat(frames,ignore_index=True); manifest=pd.concat(manifests,ignore_index=True)
    f['identical_content_different_event_candidate']=f.source_file_sha256.isin(manifest.loc[manifest.sha256.duplicated(False),'sha256'])
    # Global robust-outlier flags are for audit only, never a future-fitted exclusion rule.
    logs=np.log(f.price_usd_base.where(~f.price_invalid));groups=[f.zone,f.source]
    med=logs.groupby(groups).transform('median');mad=(logs-med).abs().groupby(groups).transform('median')
    f['price_extreme_review']=((logs-med).abs()/(1.4826*mad.replace(0,np.nan))).gt(5)
    f['content_key']=[hashlib.sha256(('|'.join([e]+list(row))).encode()).hexdigest() for e,row in zip(f.event_key,f[base.RAW_COLS].values)]
    # Content-based stable split keeps identical-row candidates together.
    f['split_half']=f.content_key.str[:8].map(lambda x:int(x,16)%2)
    base.save(manifest,'event_manifest.csv')
    for name,g in [('all_files',f),('new_uploads',f[f.upload_batch.eq('new_20260928')]),('research_accepted',f[f.included_in_research])]:
        totals,_=base.audit(g)
        (ROOT/'processed'/f'audit_{name}.json').write_text(json.dumps(totals,ensure_ascii=False,indent=2))
        shutil.copyfile(ROOT/'processed/quality_by_event.csv',ROOT/'processed'/f'quality_by_event_{name}.csv')
    base.save(f,'sales_enriched_all_files.csv')
    base.save(f[f.upload_batch.eq('new_20260928')],'new_uploads_enriched.csv')
    base.save(f[~f.included_in_research],'quarantined_records.csv')
    base.save(f[f.included_in_research],'research_accepted_records.csv')
    compare=[]
    keys={p:set(map(tuple,pd.read_csv(UPLOAD/p,dtype=str,keep_default_na=False).values)) for p in ['sales_data.csv','14-1002.csv','15-0930.csv']}
    for a,b in [('14-1002.csv','15-0930.csv'),('sales_data.csv','15-0930.csv')]:
        compare.append(dict(file_a=a,file_b=b,exact_shared_unique_rows=len(keys[a]&keys[b]),unique_a=len(keys[a]),unique_b=len(keys[b]),same_bytes=(UPLOAD/a).read_bytes()==(UPLOAD/b).read_bytes()))
    base.save(pd.DataFrame(compare),'identity_checks.csv')
    superseded=[]
    for archived in sorted((ROOT/'raw/superseded').glob('*.csv')):
        superseded.append(dict(source_file=archived.name,status='superseded_not_in_analysis',
            sha256=hashlib.sha256(archived.read_bytes()).hexdigest(),adopted_file=originalmap[archived.stem]+'.csv'))
    if superseded:base.save(pd.DataFrame(superseded),'superseded_files.csv')
    assert f.record_key.is_unique
    accepted=f[f.included_in_research]
    assert accepted.groupby('event_key').source_file.nunique().eq(1).all()
    assert accepted.groupby('source_file').source_file_sha256.first().is_unique
    assert accepted.loc[accepted.qty_unknown,'qty_known'].isna().all()
    # Q1 bins retained exactly, including right-closed <=12h boundary.
    assert list(base.time_bin(pd.Series([0,12,24,48,96,168])))==['at_or_after_start','within12h','12to24h','24to48h','48to96h','4to7d']
    print(json.dumps({'all_raw_rows':len(f),'new_raw_rows':int(f.upload_batch.eq('new_20260928').sum()),'accepted_rows':len(accepted),'accepted_events':accepted.event_key.nunique(),'quarantined_files':sorted(QUARANTINE)},ensure_ascii=False))
    return f

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--input-dir',type=Path,default=ROOT/'raw')
    run(parser.parse_args().input_dir)

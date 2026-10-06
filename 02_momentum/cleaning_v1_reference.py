"""Reproducible SeatData CSV audit and descriptive comparable-seat analysis.

Run: python analyze.py --input-dir ../upload
Dependencies: numpy, pandas, scipy, matplotlib. No network calls or paid API calls.
This is retrospective research, not an executable trading backtest.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as student_t
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
MAPPING = {'0826':'0826','0828':'0828','0829':'0829','0902':'0902','0904':'0904',
           '0905':'0905','0909':'0909','0911':'09111','0912':'09121','0916':'09161',
           '0918':'09181','0919':'0919','0923':'0923','0925':'0925','0926':'0926'}
RAW_COLS = ['Date/Time (EDT)','Source','Zone','Section','Row','Qty','Price']
BINS = ['gt7d','4to7d','48to96h','24to48h','12to24h','within12h']
LABELS = {'gt7d':'>7 days','4to7d':'4–7 days','48to96h':'48–96 hours',
          '24to48h':'24–48 hours','12to24h':'12–24 hours','within12h':'Within 12 hours'}

def save(df, name):
    df.to_csv(ROOT/'processed'/name, index=False, encoding='utf-8-sig')

def time_bin(hours):
    # Right-closed boundaries: 12 belongs to within12h; exact start is excluded.
    return pd.cut(hours, [-np.inf,0,12,24,48,96,168,np.inf],
        labels=['at_or_after_start','within12h','12to24h','24to48h','48to96h','4to7d','gt7d'],
        right=True).astype('string').fillna('invalid_time')

def load_data(input_dir):
    frames=[]; manifest=[]; hashes=[]
    for date, name in MAPPING.items():
        src=input_dir/(name+'.csv'); blob=src.read_bytes()
        sha=hashlib.sha256(blob).hexdigest(); hashes.append(sha)
        target=ROOT/'raw'/src.name
        if src.resolve()!=target.resolve(): shutil.copyfile(src,target)
        assert hashlib.sha256(target.read_bytes()).hexdigest()==sha
        f=pd.read_csv(target, dtype=str, keep_default_na=False)
        assert list(f.columns)==RAW_COLS, (name,list(f.columns))
        f['event_date']=f'2026-{date[:2]}-{date[2:]}'
        f['event_key']='HS_MSG_'+f['event_date']
        f['source_file']=src.name
        f['source_row_number']=np.arange(len(f))+2
        f['record_key']=src.name+':'+f['source_row_number'].astype(str)
        f['source_file_sha256']=sha
        frames.append(f)
        manifest.append(dict(source_file=src.name,event_date=f.event_date.iloc[0],
            event_start_local=f.event_date.iloc[0]+'T20:00:00-04:00',
            event_timezone='America/New_York',row_count=len(f),sha256=sha,
            event_identity_basis='user_confirmed_filename_mapping; CSV contains no event ID',
            start_time_basis='20:00 scheduled show time; see event_time_sources.csv',
            official_face_value_usd='',face_value_status='not_verified_at_section_row_ticket_type_level'))
    assert len(set(hashes))==len(hashes), 'Duplicate source files in selected manifest'
    excluded=[]
    for old in ['0911','0912','0916','0918']:
        src=input_dir/(old+'.csv')
        if src.exists() and old in MAPPING:
            (ROOT/'raw'/'superseded').mkdir(exist_ok=True)
            shutil.copyfile(src,ROOT/'raw'/'superseded'/src.name)
            excluded.append({'source_file':src.name,'status':'superseded_not_in_analysis',
                'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'adopted_file':MAPPING[old]+'.csv'})
    if excluded:save(pd.DataFrame(excluded),'superseded_files.csv')
    f=pd.concat(frames,ignore_index=True)
    # Preserve all seven original columns verbatim. Header explicitly says EDT:
    # primary interpretation is fixed UTC-04:00; alternative Eastern civil time is retained.
    naive=pd.to_datetime(f['Date/Time (EDT)'],format='%m-%d-%y / %I:%M %p',errors='coerce')
    f['observed_at_edt']=naive.dt.tz_localize('Etc/GMT+4')
    f['observed_at_eastern_alternative']=naive.dt.tz_localize('America/New_York',ambiguous='NaT',nonexistent='NaT')
    f['winter_timezone_ambiguous']=(f.observed_at_edt!=f.observed_at_eastern_alternative)&naive.notna()
    f['observed_at_utc']=f.observed_at_edt.dt.tz_convert('UTC')
    f['event_start_local']=pd.to_datetime(f.event_date+' 20:00:00').dt.tz_localize('America/New_York')
    f['hours_to_event']=(f.event_start_local-f.observed_at_edt).dt.total_seconds()/3600
    f['days_to_event_exact']=f.hours_to_event/24
    f['calendar_days_to_event']=(pd.to_datetime(f.event_date)-naive.dt.normalize()).dt.days
    f['time_bin']=time_bin(f.hours_to_event)
    for original,new in [('Source','source'),('Zone','zone'),('Section','section'),('Row','row')]:
        f[new]=f[original].str.strip()
    f['price_usd_base']=pd.to_numeric(f.Price,errors='coerce')
    f['qty_numeric']=pd.to_numeric(f.Qty,errors='coerce')
    f['qty_unknown']=f.qty_numeric.eq(0)
    f['qty_invalid']=f.qty_numeric.isna()|f.qty_numeric.lt(0)|f.qty_numeric.mod(1).ne(0)
    f['qty_large_review']=f.qty_numeric.gt(8) # Review threshold, not a marketplace limit.
    f['qty_known']=f.qty_numeric.where(~f.qty_unknown & ~f.qty_invalid)
    f['qty_group']=np.select([f.qty_unknown,f.qty_numeric.eq(1),f.qty_numeric.eq(2),
        f.qty_numeric.between(3,4),f.qty_numeric.ge(5)],['unknown','1','2','3-4','5+'],default='invalid')
    f['price_invalid']=~np.isfinite(f.price_usd_base)|f.price_usd_base.le(0)
    f['time_invalid']=f.observed_at_edt.isna()
    f['at_or_after_start']=f.hours_to_event.le(0)
    f['source_unknown']=~f.source.isin(['sh','vs'])
    f['row_numeric']=pd.to_numeric(f.row.where(f.row.str.fullmatch(r'\d+')),errors='coerce')
    f['section_numeric']=pd.to_numeric(f.section.where(f.section.str.fullmatch(r'\d+')),errors='coerce')
    f['row100_missing']=f.zone.eq('100 Level')&f.row.eq('')
    f['row100_review']=f.zone.eq('100 Level')&~f.row_numeric.between(1,22)&~f.row100_missing
    f['section100_review']=f.zone.eq('100 Level')&~f.section_numeric.between(101,120)
    f['section100_wc_label']=f.zone.eq('100 Level')&f.section.str.endswith('WC')
    # 101–120 and 1–22 are conservative observed common support, not assertions
    # that other seat identifiers are impossible. Review rows remain in the master.
    keys=['event_key']+RAW_COLS
    f['duplicate_candidate']=f.duplicated(keys,keep=False)
    f['duplicate_extra_candidate']=f.duplicated(keys,keep='first')
    # No sale/listing IDs in export: identical minute-level rows are NOT proven duplicates.
    cross=['event_key','Date/Time (EDT)','Section','Row','Qty','Price']
    f['cross_source_candidate']=f.groupby(cross,dropna=False)['source'].transform('nunique').gt(1)
    logs=np.log(f.price_usd_base.where(~f.price_invalid))
    groups=[f.zone,f.source]
    med=logs.groupby(groups).transform('median')
    mad=(logs-med).abs().groupby(groups).transform('median')
    f['price_extreme_review']=((logs-med).abs()/(1.4826*mad.replace(0,np.nan))).gt(5)
    f['price_above_10000_review']=f.price_usd_base.gt(10000)
    f['observed_calendar_week']=naive.dt.strftime('%Y-%W')
    f['eligible_price_prestart']=~f.price_invalid & ~f.time_invalid & f.hours_to_event.gt(0) & ~f.source_unknown
    f['eligible_100_common_seats']=f.eligible_price_prestart & f.zone.eq('100 Level') & ~f.row100_missing & ~f.row100_review & ~f.section100_review
    f['eligible_100_main_30d']=f.eligible_100_common_seats & f.hours_to_event.le(720)
    f['official_face_value_usd']=np.nan
    f['official_face_value_status']='not_verified'
    save(pd.DataFrame(manifest),'event_manifest.csv')
    return f

def audit(f):
    flags=['qty_unknown','qty_invalid','qty_large_review','price_invalid','time_invalid',
        'at_or_after_start','source_unknown','row100_missing','row100_review','section100_review',
        'duplicate_candidate','duplicate_extra_candidate','cross_source_candidate',
        'price_extreme_review','price_above_10000_review','section100_wc_label','winter_timezone_ambiguous']
    rows=[]
    for ev,g in [('ALL',f)]+list(f.groupby('event_date',sort=True)):
        r={'event_date':ev,'raw_rows':len(g),'100_level_rows':int(g.zone.eq('100 Level').sum()),
           'eligible_100_main_30d':int(g.eligible_100_main_30d.sum())}
        r.update({x:int(g[x].sum()) for x in flags})
        r.update({'missing_'+c:int(g[c].eq('').sum()) for c in RAW_COLS})
        rows.append(r)
    save(pd.DataFrame(rows),'quality_by_event.csv')
    save(f[f[flags[:-1]].any(axis=1)],'flagged_records.csv')
    save(f[f.duplicate_candidate|f.cross_source_candidate],'duplicate_candidates.csv')
    zones=f.groupby('zone',dropna=False).agg(records=('record_key','size'),events=('event_key','nunique')).reset_index()
    save(zones.sort_values('records',ascending=False),'seat_categories.csv')
    q=f.groupby(['source','Qty'],dropna=False).size().rename('records').reset_index()
    save(q,'quantity_distribution.csv')
    return rows[0],zones

def summarize(f, group):
    return f.groupby(group,observed=True,dropna=False).agg(
        records=('record_key','size'),events=('event_key','nunique'),
        median_price_usd=('price_usd_base','median'),mean_price_usd=('price_usd_base','mean'),
        p25_price_usd=('price_usd_base',lambda s:s.quantile(.25)),
        p75_price_usd=('price_usd_base',lambda s:s.quantile(.75)),
        qty_unknown_records=('qty_unknown','sum'),known_quantity_sum=('qty_known',lambda s:s.sum(min_count=1)),
        first_observed=('observed_at_edt','min'),last_observed=('observed_at_edt','max')).reset_index()

def design(f,calendar_control=False):
    parts=[pd.DataFrame({'intercept':np.ones(len(f))},index=f.index)]
    for k in ['event_key','section','row','source','qty_group']:
        parts.append(pd.get_dummies(f[k],prefix=k,drop_first=True,dtype=float))
    if calendar_control:
        parts.append(pd.get_dummies(f.observed_calendar_week,prefix='calendar_week',drop_first=True,dtype=float))
    for b in BINS[1:]: parts.append(pd.DataFrame({'bin_'+b:f.time_bin.eq(b).astype(float)}))
    return pd.concat(parts,axis=1)

def fit_model(f,name,calendar_control=False):
    f=f.reset_index(drop=True)
    Xdf=design(f,calendar_control); X=Xdf.to_numpy(); y=np.log(f.price_usd_base.to_numpy())
    beta,resids,rank,singular=np.linalg.lstsq(X,y,rcond=None)
    assert rank==X.shape[1], (name,rank,X.shape)
    resid=y-X@beta; bread=np.linalg.inv(X.T@X); meat=np.zeros_like(bread)
    events=f.event_key.unique(); G=len(events); n,p=X.shape
    for event in events:
        mask=f.event_key.eq(event).to_numpy(); score=X[mask].T@resid[mask]; meat+=np.outer(score,score)
    cov=(G/(G-1))*((n-1)/(n-p))*bread@meat@bread
    se=np.sqrt(np.maximum(np.diag(cov),0)); critical=student_t.ppf(.975,G-1)
    results=[]; coef=dict(zip(Xdf.columns,beta))
    Xref=X.copy()
    for j,c in enumerate(Xdf.columns):
        if c.startswith('bin_'): Xref[:,j]=0
    ref_geo=np.exp((Xref@beta).mean())
    for b in BINS:
        j=list(Xdf.columns).index('bin_'+b) if b!='gt7d' else None
        v=beta[j] if j is not None else 0.; s=se[j] if j is not None else 0.
        g=f[f.time_bin.eq(b)]
        results.append(dict(model=name,time_bin=b,records=len(g),events=g.event_key.nunique(),
            coefficient_log=v,cluster_se=s,adjusted_index=100*np.exp(v),
            index_lower_95=100*np.exp(v-critical*s),index_upper_95=100*np.exp(v+critical*s),
            pct_vs_reference=100*np.expm1(v),standardized_geometric_price_usd=ref_geo*np.exp(v),
            model_n=n,model_parameters=p,clusters=G))
    # A retrospective comparable-seat benchmark for each observation. Not point-in-time.
    f['retrospective_benchmark_7_30d_usd']=np.exp(Xref@beta)
    f['retrospective_price_index']=100*f.price_usd_base/f.retrospective_benchmark_7_30d_usd
    f['benchmark_use']='retrospective_descriptive_only_not_trading_signal'
    table=pd.DataFrame({'term':Xdf.columns,'coefficient_log':beta,'event_cluster_se':se})
    save(table,'coefficients_'+name+'.csv')
    return pd.DataFrame(results), f, dict(n=n,p=p,rank=int(rank),r2=float(1-np.sum(resid**2)/np.sum((y-y.mean())**2)),ref_geo=float(ref_geo))

def analysis(f):
    all100=f[f.zone.eq('100 Level') & f.eligible_price_prestart]
    rawsummary=summarize(all100,['time_bin'])
    save(rawsummary,'100_level_bins_full_history.csv')
    save(summarize(f[f.eligible_price_prestart],['zone','time_bin']),'all_zones_bins_full_history.csv')
    main=f[f.eligible_100_main_30d].copy()
    summary=summarize(main,['time_bin']);save(summary,'100_level_bins_main_30d.csv')
    save(summarize(main,['event_date','time_bin']),'100_level_event_bins_30d.csv')
    save(summarize(main,['source','time_bin']),'100_level_source_bins_30d.csv')
    save(summarize(main,['section','row','source','time_bin']),'100_level_seat_bins_30d.csv')
    out,bench,info=fit_model(main,'main_30d')
    save(bench,'100_level_main_with_retrospective_benchmark.csv')
    variants=[out]
    # Prespecified robustness checks, not a search over profitable specifications.
    configs=[('sh_only',main[main.source.eq('sh')]),
             ('known_qty_only',main[~main.qty_unknown & ~main.qty_invalid]),
             ('dedup_sensitivity',main[~main.duplicate_extra_candidate]),
             ('exclude_extreme_review',main[~main.price_extreme_review]),
             ('all_history',f[f.eligible_100_common_seats]),
             ('early_8_events',main[main.event_date.le('2026-09-11')]),
             ('late_7_events',main[main.event_date.ge('2026-09-12')])]
    for name,g in configs:
        r,_,_=fit_model(g,name);variants.append(r)
    calendar,calbench,_=fit_model(main,'calendar_week_control',calendar_control=True);variants.append(calendar)
    calbench['benchmark_use']='retrospective_with_calendar_week_controls_not_trading_signal'
    save(calbench,'100_level_calendar_adjusted_retrospective_benchmark.csv')
    for shift in [-1,1]:
        alt=f.copy();alt['hours_to_event']=alt.hours_to_event+shift
        alt['time_bin']=time_bin(alt.hours_to_event)
        valid=~alt.price_invalid&~alt.time_invalid&~alt.source_unknown&alt.zone.eq('100 Level')&~alt.row100_missing&~alt.row100_review&~alt.section100_review&alt.hours_to_event.gt(0)&alt.hours_to_event.le(720)
        r,_,_=fit_model(alt[valid],f'start_shift_{shift:+d}h');variants.append(r)
    save(pd.concat(variants,ignore_index=True),'adjusted_price_indices.csv')
    # Direct seat matching sanity check with equal weighting per eligible stratum.
    sk=['event_key','section','row','source']
    grouped=main.groupby(sk+['time_bin'],observed=True).price_usd_base.agg(['median','size']).reset_index()
    ref=grouped[grouped.time_bin.eq('gt7d') & grouped['size'].ge(3)].rename(columns={'median':'ref_median','size':'ref_n'}).drop(columns='time_bin')
    match=grouped.merge(ref,on=sk,how='inner');match=match[match['size'].ge(2)]
    match['ratio']=match['median']/match.ref_median
    save(match,'matched_seat_comparisons.csv')
    matched=match.groupby('time_bin').agg(strata=('ratio','size'),events=('event_key','nunique'),median_ratio=('ratio','median')).reset_index()
    save(matched,'matched_seat_summary.csv')
    # Cross-event variation; raw event medians do not fully control seat mix.
    ev=main.groupby(['event_date','time_bin'],observed=True).price_usd_base.median().unstack()
    ev=ev.div(ev['gt7d'],axis=0)*100
    save(ev.reset_index(),'event_median_indices.csv')
    fig,ax=plt.subplots(figsize=(10,5.5),layout='constrained')
    positions=np.arange(len(BINS)); inds=out.set_index('time_bin').loc[BINS]
    ax.errorbar(positions,inds.adjusted_index,yerr=[inds.adjusted_index-inds.index_lower_95,inds.index_upper_95-inds.adjusted_index],fmt='o-',color='#175c9e',capsize=4,lw=2,label='Adjusted comparable-seat index')
    ci=calendar.set_index('time_bin').loc[BINS]
    ax.errorbar(positions+.06,ci.adjusted_index,yerr=[ci.adjusted_index-ci.index_lower_95,ci.index_upper_95-ci.adjusted_index],fmt='s-',color='#d16a20',capsize=4,lw=2,label='Also controlling for calendar week')
    ax.axhline(100,color='#667085',ls='--',lw=1)
    ax.set_xticks(positions,['7–30 days','4–7 days','48–96h','24–48h','12–24h','≤12h'])
    ax.set_ylabel('Price index (7–30 days = 100)');ax.set_xlabel('Time remaining to scheduled start')
    ax.set_title('Harry Styles at MSG: 100 Level prices near the show',loc='left',fontweight='bold')
    ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.18)
    ax.legend(frameon=False,loc='lower left',fontsize=9)
    for x,row in zip(positions,inds.itertuples()): ax.annotate(f'{row.adjusted_index:.1f}',(x,row.adjusted_index),xytext=(0,10),textcoords='offset points',ha='center',fontsize=10)
    fig.text(.02,-.035,'Controls: event, section, exact numeric row, source, quantity group. Bars: event-clustered 95% intervals.\n15 related events; retrospective association, not a causal effect or trading return.',fontsize=9,color='#475467')
    fig.savefig(ROOT/'figures'/'price_index.png',dpi=180,bbox_inches='tight');plt.close(fig)
    return out,summary,matched,info,pd.concat(variants,ignore_index=True)

def tests(f):
    h=pd.Series([-1,0,.001,11.99,12,12.01,24,24.01,48,48.01,96,96.01,168,168.01])
    expected=['at_or_after_start','at_or_after_start','within12h','within12h','within12h','12to24h','12to24h','24to48h','24to48h','48to96h','48to96h','4to7d','4to7d','gt7d']
    assert list(time_bin(h))==expected
    assert f.record_key.is_unique
    assert len(f)==23424
    assert f.zone.eq('100 Level').sum()==9573
    assert f.loc[f.qty_unknown,'qty_known'].isna().all()
    assert f.loc[f.eligible_100_main_30d,'hours_to_event'].between(0,720,inclusive='right').all()
    assert f.groupby('event_key').source_file.nunique().eq(1).all()
    assert len(summarize(f[f.zone.eq('100 Level')&f.eligible_price_prestart],['time_bin']))==6

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--input-dir',type=Path,default=ROOT/'raw');args=parser.parse_args()
    for p in ['raw','processed','figures']: (ROOT/p).mkdir(parents=True,exist_ok=True)
    f=load_data(args.input_dir);a,z=audit(f);tests(f)
    indices,summary,matched,info,variants=analysis(f)
    save(f,'sales_enriched_all_records.csv')
    payload={'audit':a,'model':info,'indices':indices.to_dict('records'),
        'matched':matched.to_dict('records'),'selected_files':MAPPING,
        'bin_rule':'(0,12],(12,24],(24,48],(48,96],(96,168],(168,infinity); h<=0 separate',
        'as_of_local':'2026-09-27 America/Chicago','q2_status':'protocol only; no continuation claim'}
    (ROOT/'processed'/'results.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False,default=str))
    print(json.dumps(payload,indent=2,ensure_ascii=False,default=str))
    print(variants.pivot(index='time_bin',columns='model',values='adjusted_index').round(2).to_string())

if __name__=='__main__':main()

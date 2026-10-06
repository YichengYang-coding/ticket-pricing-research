from pathlib import Path
import json, itertools, hashlib, os
import numpy as np
import pandas as pd
from scipy.linalg import lstsq
from scipy.stats import t

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'outputs'; OUT.mkdir(exist_ok=True)
def save_csv(frame,path):
    path=Path(path);temp=path.with_suffix(path.suffix+'.pending')
    frame.to_csv(temp,index=False);os.replace(temp,path)
raw=pd.read_csv(ROOT/'data/Harry_cleaned_sales.csv',low_memory=False)
accepted=raw[raw.included_in_research].copy()
all100=accepted[accepted.zone.eq('100 Level')|accepted.section_numeric.between(101,120)].copy()
save_csv(all100,OUT/'100_level_records_audited.csv')
ordinary=all100[all100.Section.astype(str).str.fullmatch(r'10[1-9]|11[0-9]|120')].copy()
ordinary['s']=pd.to_numeric(ordinary.Section).astype(int)
ordinary['r']=pd.to_numeric(ordinary.Row,errors='coerce')
valid=(ordinary.r.between(1,22)&ordinary.r.eq(ordinary.r.round())&ordinary.valid_prestart&ordinary.price_usd_base.gt(0))
d=ordinary[valid & ordinary.source.eq('sh')].copy()
d['r']=d.r.astype(int)
d['week']=pd.to_datetime(d.observed_at_utc,utc=True).dt.tz_convert('America/New_York').dt.strftime('%G-%V')
d['lead']=pd.cut(d.hours_to_event,[0,12,24,48,96,168,336,672,1344,2688,np.inf],labels=False).astype(str)
d['event']=d.event_date
d['q']=d.qty_group.astype(str)
d['y']=np.log(d.price_usd_base)
geo={107:'A',117:'A',106:'B',108:'B',116:'B',118:'B',105:'C',109:'C',115:'C',119:'C',104:'D',110:'D',114:'D',120:'D',101:'E',102:'E',103:'E',111:'E',112:'E',113:'E'}
d['geo']=d.s.map(geo)

def fit(frame,row_effect=True,section_effect=True,interactions=False):
    factors=['event','week','lead','q']+(['s'] if section_effect else [])+(['r'] if row_effect else [])
    xx=pd.get_dummies(frame[factors].astype(str),drop_first=True,dtype=float)
    if interactions:
        for geom in ['A','B','C','DE']:
            for band in ['1-2','3-6','7-10','11-15']:
                v=(frame.econ.eq(geom)&frame.rowband.eq(band)).astype(float)
                if v.sum():xx['band_'+geom+'_'+band]=v
    xx.insert(0,'const',1.)
    X=xx.to_numpy();y=frame.y.to_numpy()
    # Equal total weight per event. Huber loss downweights extreme log prices;
    # it does not erase or relabel observations.
    base=1/frame.groupby('event').event.transform('size').to_numpy()
    base=base/base.mean();w=base.copy()
    b=lstsq(X*np.sqrt(w[:,None]),y*np.sqrt(w),lapack_driver='gelsy')[0]
    for it in range(25):
        resid=y-X@b;scale=1.4826*np.median(np.abs(resid-np.median(resid)))
        hub=np.minimum(1,1.345*max(scale,1e-8)/np.maximum(abs(resid),1e-8))
        w=base*hub
        bn=lstsq(X*np.sqrt(w[:,None]),y*np.sqrt(w),lapack_driver='gelsy')[0]
        if np.max(abs(bn-b))<1e-7:b=bn;break
        b=bn
    resid=y-X@b
    return {'b':pd.Series(b,index=xx.columns),'resid':resid,'X':X,'cols':list(xx.columns),'w':w,'rank':int(np.linalg.matrix_rank(X)),'n':len(y),'iterations':it+1}

main=fit(d)
fits={'all_history':main,'within30days':fit(d[d.days_to_event_exact.le(30)]),
      'completed_events':fit(d[d.event_date.le('2026-09-26')]),
      'exclude_flags':fit(d[~d.price_extreme_review & ~d.duplicate_extra_candidate]),
      'late_sale_period':fit(d[pd.to_datetime(d.observed_at_utc,utc=True).ge(pd.Timestamp('2026-09-01',tz='UTC'))])}
fits['common_rows_6_20']=fit(d[d.r.between(6,20)])

sections=[]
for s,g in ordinary.groupby('s'):
    gp=g[g.r.between(1,22)]
    modelg=d[d.s.eq(s)]
    observed=sorted(gp.r.dropna().astype(int).unique())
    sect={'section':s,'proposed_geo':geo[s],'all_sources_records':len(g),'sh_model_records':len(modelg),
          'observed_min_row':min(observed),'observed_max_row':max(observed),'observed_distinct_rows':len(observed),
          'observed_rows':','.join(map(str,observed)),
          'unobserved_in_span':','.join(map(str,sorted(set(range(min(observed),max(observed)+1))-set(observed)))),
          'nonnumeric_or_outside_1_22':int((~g.r.between(1,22)).sum()),
          'raw_all_history_sh_median':modelg.price_usd_base.median()}
    for name,model in fits.items():
        vals={k:float(model['b'].get('s_'+str(k),0)) for k in range(101,121)}
        anchor=np.mean([vals[k] for k in [101,102,103,111,112,113]])
        sect[name+'_index']=float(100*np.exp(vals[s]-anchor))
    sections.append(sect)
sec=pd.DataFrame(sections)
save_csv(sec,OUT/'section_summary.csv')
rows=[]
for r,g in d.groupby('r'):
    item={'row':r,'n':len(g),'n_sections':g.s.nunique(),'n_events':g.event.nunique(),'raw_median':g.price_usd_base.median()}
    for name,m in fits.items():
        if name=='common_rows_6_20':continue
        v=float(m['b'].get('r_'+str(r),0));base=float(m['b'].get('r_22',0))
        item[name+'_index']=100*np.exp(v-base)
    rows.append(item)
rr=pd.DataFrame(rows).sort_values('row');save_csv(rr,OUT/'row_effects.csv')

# Explore four contiguous row groups on pooled adjusted row effects.
# This is descriptive selection on the available data, not out-of-sample validation.
cut_results=[]
for name in [x for x in fits if x!='common_rows_6_20']:
    y=np.log(rr[name+'_index'].to_numpy()/100);weights=rr.n.to_numpy()
    for cuts in itertools.combinations(range(3,21),3):
        bounds=(0,)+cuts+(22,)
        if min(np.diff(bounds))<3:continue
        loss=0;means=[];counts=[]
        for a,b in zip(bounds[:-1],bounds[1:]):
            yy=y[a:b];ww=weights[a:b];mu=np.average(yy,weights=ww)
            loss+=np.sum(ww*(yy-mu)**2);means.append(float(mu));counts.append(int(ww.sum()))
        cut_results.append({'model':name,'cuts':','.join(map(str,cuts)),'loss':float(loss),'group_sizes':','.join(map(str,counts))})
cuts_df=pd.DataFrame(cut_results).sort_values(['model','loss']);save_csv(cuts_df,OUT/'row_cut_candidates.csv')

d['econ']=d.geo.replace({'D':'DE','E':'DE'})
d['rowband']=pd.cut(d.r,[0,2,6,10,15,22],labels=['1-2','3-6','7-10','11-15','16-22']).astype(str)
inter=fit(d,row_effect=False,interactions=True)
band_rows=[]
for (g,band),v in d.groupby(['econ','rowband']):
    b=float(inter['b'].get('band_'+g+'_'+band,0))
    band_rows.append({'section_group':g,'row_band':band,'n':len(v),'n_sections':v.s.nunique(),'n_events':v.event.nunique(),'adjusted_index_rear100':100*np.exp(b),'raw_median':v.price_usd_base.median()})
save_csv(pd.DataFrame(band_rows),OUT/'row_bands_by_section_group.csv')
print('\nROW BANDS BY GEOGRAPHY\n'+pd.DataFrame(band_rows).round(1).to_string(index=False))

# Save directly observed section x row counts/medians independently of adjustments.
cross=d.groupby(['s','r']).agg(n=('y','size'),events=('event','nunique'),median=('price_usd_base','median'),p25=('price_usd_base',lambda x:x.quantile(.25)),p75=('price_usd_base',lambda x:x.quantile(.75))).reset_index()
save_csv(cross,OUT/'section_row_observations.csv')
d['section_log_effect']=d.s.map({s:main['b'].get('s_'+str(s),0) for s in range(101,121)})
d['row_log_effect']=d.r.map({r:main['b'].get('r_'+str(r),0) for r in range(1,23)})
d['seat_adjusted_log_price']=main['resid']+d.section_log_effect+d.row_log_effect
save_csv(d,OUT/'model_records.csv')
save_csv(pd.DataFrame([{'model':n,'term':term,'coefficient':v} for n,m in fits.items() for term,v in m['b'].items()]),OUT/'model_coefficients.csv')
assert len(pd.read_csv(OUT/'model_records.csv',low_memory=False))==len(d)
audit={'input_rows':len(raw),'accepted_rows':len(accepted),'accepted_events':accepted.event_date.nunique(),'quarantined_rows':len(raw)-len(accepted),'candidate_100_rows':len(all100),'ordinary_exact_section_rows':len(ordinary),'model_rows':len(d),'model_events':d.event.nunique(),'outside_numeric_1_22':int((ordinary.r.notna()&~ordinary.r.between(1,22)).sum()),'nonnumeric_or_missing_rows':int(ordinary.r.isna().sum()),'model_extreme_flags':int(d.price_extreme_review.sum()),'model_duplicate_extras':int(d.duplicate_extra_candidate.sum()),'model_qty_unknown':int(d.qty_unknown.sum()),'source_sha256':hashlib.sha256((ROOT/'data/Harry_cleaned_sales.csv').read_bytes()).hexdigest(),'models':{n:{'n':m['n'],'p':len(m['b']),'rank':m['rank'],'iterations':m['iterations']} for n,m in fits.items()}}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2))
print(json.dumps(audit,indent=2));print('\nSECTIONS\n'+sec[['section','sh_model_records','observed_min_row','observed_max_row','all_history_index','within30days_index','completed_events_index','late_sale_period_index']].round(1).to_string(index=False));print('\nROWS\n'+rr.round(1).to_string(index=False));print('\nBEST ROW CUTS\n'+cuts_df.groupby('model').head(3).to_string(index=False))

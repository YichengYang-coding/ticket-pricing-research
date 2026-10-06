"""Recompute stable inference and paired-sample diagnostic from saved panels."""
import json
import numpy as np
import pandas as pd
import analyze_q2 as q

def loadpanel(v):
    p=pd.read_csv(q.ROOT/'processed'/f'panel_{v}.csv')
    for c in ['as_of','label_end','label_end_6d']:p[c]=pd.to_datetime(p[c],utc=True).dt.tz_convert(q.TZ)
    return p

def run():
    coefs=[];metrics=[]
    for v in ['all_sources','sh_only','dedup','under_10000']:
        p=loadpanel(v)
        for k in (['main','split','nonoverlap'] if v in ['all_sources','sh_only'] else ['main']):
            coefs.append(q.explanatory(p,k,v))
            pred=q.walkforward(p,k,v);metrics.extend(q.metrics(pred,v,k,0))
        if v=='all_sources':
            pred=q.walkforward(p,'main',v,gap=6);metrics.extend(q.metrics(pred,v,'main',6))
    p=loadpanel('all_sources')
    eligible=q.select(p,'split')[['xx','yy','mx']].notna().all(axis=1)
    paired=p.copy();paired.loc[~eligible,['x','y']]=np.nan
    coefs.append(q.explanatory(paired,'main','same_sample_as_split'))
    c=pd.DataFrame(coefs);q.save(c,'conditional_coefficients.csv')
    m=pd.DataFrame(metrics);q.save(m,'oos_metrics.csv');q.plot(c,m)
    s=json.loads((q.ROOT/'processed/model_summary.json').read_text());s['coefficients']=coefs;s['metrics']=metrics
    (q.ROOT/'processed/model_summary.json').write_text(json.dumps(s,ensure_ascii=False,indent=2,default=str))
    primary=pd.read_csv(q.ROOT/'processed/predictions_all_sources_main_gap0.csv')
    primary['as_of']=pd.to_datetime(primary.as_of,utc=True).dt.tz_convert(q.TZ)
    latest=primary[primary.as_of.eq(q.LAST)].copy();latest['status']='historical_snapshot_not_prospectively_issued_at_as_of'
    q.save(latest,'latest_research_signals_not_trade_orders.csv')
    print(c[['variant','kind','n','coefficient','lower95','upper95']].to_string(index=False))

if __name__=='__main__':run()

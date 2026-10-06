"""Identical estimators copied from the completed BSB study; see protocol.md."""
def design(g,cats,extra=()):
 x=pd.DataFrame({'intercept':1.,'order10':g.order10},index=g.index)
 if cats:x=pd.concat([x,pd.get_dummies(g[cats].astype(str),drop_first=True,dtype=float)],axis=1)
 for c in extra:x[c]=g[c].astype(float)
 return x

def meat(score,labels,rank):
 code,groups=pd.factorize(labels);G=len(groups);n,k=score.shape;s=np.zeros((G,k));np.add.at(s,code,score)
 return s.T@s*(G/(G-1))*((n-1)/(n-rank)),G

def price_fit(raw,label,cell=False,allreserved=False,extra=(),cohort=False,save_main=False):
 g=raw[raw.other_reserved_seat if allreserved else raw.ordinary100_seat].copy()
 cats=(['cell'] if cell else ['section','zone_row' if allreserved else 'row'])+['qty_group','lead_bucket','weekday']
 if cohort:cats+=['cohort']
 x=design(g,cats,extra)
 if allreserved and not cell:
  # Section already identifies level, so each level needs its own baseline row.
  for zone in sorted(g.zone.unique())[1:]:
   baseline=sorted(g.loc[g.zone.eq(zone),'zone_row'].unique())[0]
   x=x.drop(columns=['zone_row_'+baseline],errors='ignore')
 X=x.to_numpy(float);y=np.log(g.price_usd_base.to_numpy(float))
 w=(1/g.groupby('event_date').event_date.transform('size')).to_numpy();Xw=X*np.sqrt(w)[:,None]
 b,_,rank,sv=linalg.lstsq(Xw,y*np.sqrt(w),cond=1e-10,lapack_driver='gelsd')
 assert rank==X.shape[1],(label,rank,X.shape)
 u=y-X@b;bread=np.linalg.pinv(Xw.T@Xw,rcond=1e-10);score=X*(w*u)[:,None]
 a,G=meat(score,g.event_date,rank);c,H=meat(score,g.sale_week,rank);ac,J=meat(score,g.event_date+'|'+g.sale_week,rank)
 variances=[float((bread@v@bread)[1,1]) for v in [a,c,a+c-ac]]
 se=np.sqrt(max(variances+[0.]));df=min(G,H)-1;ci=b[1]+np.array([-1,1])*stats.t.ppf(.975,df)*se
 r=dict(model=label,n_records=len(g),n_events=G,n_sale_weeks=H,rank=int(rank),beta=float(b[1]),se=float(se),df=df,pct_per_10=float(np.expm1(b[1])*100),ci_low_pct=float(np.expm1(ci[0])*100),ci_high_pct=float(np.expm1(ci[1])*100),p=float(2*stats.t.sf(abs(b[1]/se),df)))
 prices.append(r)
 if save_main:
  g['adjusted_log_price']=y-(X@b-b[0]-X[:,1]*b[1])
  ix=g.groupby(['event_date','order']).agg(n_price=('record_key','size'),raw_median_usd=('price_usd_base','median'),adjusted_log_mean=('adjusted_log_price','mean')).reset_index()
  baseline=np.exp(ix.loc[ix.order.le(6),'adjusted_log_mean']).mean()
  ix['adjusted_index']=100*np.exp(ix.adjusted_log_mean)/baseline
  ix['fitted_index']=100*np.exp(b[0]+b[1]*ix.order/10)/baseline
  save(ix,'price_event_indices.csv');save(pd.DataFrame({'term':x.columns,'coefficient':b}),'price_coefficients.csv')
  save(g[['record_key','event_date','order','observed_at_utc','section','row','qty_group','lead','price_usd_base','adjusted_log_price']],'price_main_records.csv')
  assert np.allclose(pd.Series(w,index=g.index).groupby(g.event_date).sum(),1)
 return r

def count_fit(a,label,outcome='ordinary100_count',cohort=False,save_main=False):
 a=a.copy();x=design(a,['weekday']+(['cohort'] if cohort else []));X=x.to_numpy(float);y=a[outcome].to_numpy(float);n,k=X.shape
 assert np.linalg.matrix_rank(X)==k
 def fn(b):
  z=X@b;mu=np.exp(z);return np.sum(mu-y*z),X.T@(mu-y)
 b0=np.zeros(k);b0[0]=np.log(y.mean());fit=optimize.minimize(fn,b0,jac=True,method='BFGS',options={'gtol':1e-8,'maxiter':2000})
 b=fit.x;mu=np.exp(X@b);assert np.abs(fn(b)[1]).max()<1e-4,(label,fit.message)
 bread=np.linalg.pinv(X.T@(mu[:,None]*X));score=X*(y-mu)[:,None]
 m,G=meat(score,a.event_week,k);disp=max(1.,np.sum((y-mu)**2/mu)/(n-k))
 variances=[float((bread@m@bread)[1,1]),float((bread@score.T@score@bread*n/(n-k))[1,1]),float(bread[1,1]*disp)]
 se=np.sqrt(max(variances+[0.]));df=G-1;ci=b[1]+np.array([-1,1])*stats.t.ppf(.975,df)*se
 r=dict(model=label,outcome=outcome,n_events=n,n_records=int(y.sum()),n_event_weeks=G,beta=float(b[1]),se=float(se),df=df,dispersion=float(disp),pct_per_10=float(np.expm1(b[1])*100),ci_low_pct=float(np.expm1(ci[0])*100),ci_high_pct=float(np.expm1(ci[1])*100),p=float(2*stats.t.sf(abs(b[1]/se),df)))
 counts.append(r)
 if save_main:
  a['fitted_count']=mu;save(a,'activity_main_events.csv');save(pd.DataFrame({'term':x.columns,'coefficient':b}),'activity_coefficients.csv')
 return r

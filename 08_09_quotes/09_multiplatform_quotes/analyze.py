from pathlib import Path
import ast,hashlib,json,os,runpy,shutil,zipfile
from datetime import datetime
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'outputs'; INPUT=ROOT/'input'; INPUT.mkdir(exist_ok=True)
ASOF=pd.Timestamp('2026-09-30T01:45:02Z')
UPDATE_ASOF=pd.Timestamp('2026-09-30T02:15:33Z')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def textsave(p,s):
 t=p.with_suffix(p.suffix+'.pending');t.write_text(s,encoding='utf-8');os.replace(t,p)
def csvsave(d,name):
 p=OUT/name;t=p.with_suffix('.csv.pending');d.to_csv(t,index=False,encoding='utf-8-sig');os.replace(t,p)
def cleanjson(v):
 if isinstance(v,dict):return {str(k):cleanjson(x) for k,x in v.items()}
 if isinstance(v,list):return [cleanjson(x) for x in v]
 if isinstance(v,np.generic):return v.item()
 if isinstance(v,float) and not np.isfinite(v):return None
 return v

# Keep the calibration and frozen model as reproducible input, never refit with asks.
sources=[(ROOT.parent/'msg_quotes_20260929/outputs/quote_observations.csv','fee_observations.csv'),(ROOT.parent/'msg_update_20260929/outputs/frozen_forecast_model.json','frozen_forecast_model.json'),(ROOT.parent/'msg_update_20260929/model_v1_frozen.py','model_v1_frozen.py'),(ROOT.parent/'msg_update_20260929/outputs/Harry_current_sales_20260929.csv','Harry_current_sales_20260929.csv')]
for src,name in sources:
 if not (INPUT/name).exists():shutil.copyfile(src,INPUT/name)
fee=pd.read_csv(INPUT/'fee_observations.csv')
fee=fee.drop_duplicates(['platform','event_date','section','row','quantity','base','fee','discount','total']).copy()
fee['rate']=fee.fee/fee.base
fee_rate=float(fee.rate.mean());fee_low=float(fee.rate.min());fee_high=float(fee.rate.max())
assert len(fee)==16
assert abs(fee_rate-0.1460668591550234)<1e-12
assert np.abs(fee.base+fee.fee-fee.discount-fee.total).max()<1e-8
csvsave(fee,'fee_calibration_16.csv')
fr=ROOT/'fee_source_images';fr.mkdir(exist_ok=True)
for fn in fee.file:
 src=ROOT.parent/'msg_quotes_20260929/raw'/fn
 if not (fr/fn).exists():shutil.copyfile(src,fr/fn)

meta=json.loads((ROOT/'work/images.json').read_text())
trans=runpy.run_path(str(ROOT/'work/manual_extract.py'))['DATA']
update_meta=json.loads((ROOT/'work/update_images.json').read_text())
update_trans=runpy.run_path(str(ROOT/'work/manual_extract_update.py'))['DATA']
for m in meta:
 m['snapshot_batch']='原始批次';m['raw_file_relativepath']='raw/'+m['path']
for m in update_meta:
 m['snapshot_batch']='重拍批次';m['raw_file_relativepath']=m['path']
meta+=update_meta
trans.update(update_trans)
assert set(trans)=={x['image_id'] for x in meta}
zip_path=ROOT.parent/'upload/01-ticket.zip'
zip_times={}
if zip_path.exists():
 with zipfile.ZipFile(zip_path) as z:
  for f in z.infolist():
   if not f.is_dir():zip_times[f.filename]=datetime(*f.date_time).isoformat(' ')
 textsave(INPUT/'zip_metadata.json',json.dumps({'zip_sha256':digest(zip_path),'zip_bytes':zip_path.stat().st_size,'member_modified_times':zip_times},ensure_ascii=False,indent=2))
else:zip_times=json.loads((INPUT/'zip_metadata.json').read_text())['member_modified_times']
update_zip=ROOT.parent/'upload/01-sad.zip'
if update_zip.exists():
 with zipfile.ZipFile(update_zip) as z:
  update_times={'raw_update_seatgeek/'+f.filename:datetime(*f.date_time).isoformat(' ') for f in z.infolist() if not f.is_dir()}
 textsave(INPUT/'sad_zip_metadata.json',json.dumps({'zip_sha256':digest(update_zip),'zip_bytes':update_zip.stat().st_size,'member_modified_times':update_times},ensure_ascii=False,indent=2))
else:update_times=json.loads((INPUT/'sad_zip_metadata.json').read_text())['member_modified_times']
zip_times.update(update_times)
rows=[]
for image in meta:
 image_id=image['image_id'];rel=image['path'];platform,folder,_=rel.split('/')
 is_update=image['snapshot_batch']=='重拍批次'
 if is_update:platform='seatgeek'
 asof=UPDATE_ASOF if is_update else ASOF
 platform={'gametime':'Gametime','seatgeek':'SeatGeek','tickpick':'TickPick'}[platform]
 event={'0930':'2026-09-30','1002':'2026-10-02','1003':'2026-10-03','1007':'2026-10-07','新建文件夹':'2026-10-07'}.get(folder)
 event_status='按用户文件夹标注'
 if event is None:event_status='缺少场次日期'
 elif platform=='SeatGeek' and folder in ['0930','1002'] and not is_update:event_status='旧图日期未证实，隔离保留'
 for i,rec in enumerate(trans[image_id],1):
  section,row,price=rec[:3];note=rec[3] if len(rec)>3 else ''
  if folder=='新建文件夹':note+='；用户本次明确确认为2026-10-07，原文件夹名保留'
  sn=int(section) if str(section).isdigit() else None
  ordinary=sn is not None and 101<=sn<=120
  known_price=price is not None
  exclude=known_price and price>1000
  est=round(price*(1+fee_rate),2) if known_price and platform=='SeatGeek' else price
  exclude_policy=exclude or (est is not None and est>1000)
  event_ok=event_status=='按用户文件夹标注'
  row_ok=ordinary and row is not None and 3<=row<=22
  status=[]
  if not known_price:status.append('价格被遮挡')
  if exclude:status.append('展示价超过1000，排除')
  elif exclude_policy:status.append('平均费率估算后超过1000，主参考表排除')
  if not ordinary:status.append('普通100 Level范围外')
  if not event_ok:status.append(event_status)
  if ordinary and row is None:status.append('Row未确认')
  if ordinary and row is not None and not row_ok:status.append('Row超出模型3至22排')
  if not status:status=['可作座位报价参考，非可执行订单']
  row_method=('TickPick高亮排号' if platform=='TickPick' else 'Gametime指针与排号追踪') if row is not None else '未确认'
  time_zip=zip_times.get(rel)
  rowdict={'observation_id':f'{image_id}-Q{i:02}','image_id':image_id,'platform':platform,'event_date_folder':event,'event_identity_status':event_status,'section_label':str(section),'section_numeric':sn,'row':row,'row_reading_method':row_method,'displayed_price_usd':price,'price_basis':'费用前，按用户说明' if platform=='SeatGeek' else '含买方费用，按用户说明','applied_buyer_fee_rate':fee_rate if platform=='SeatGeek' else None,'estimated_buyer_fee_usd':round(price*fee_rate,2) if known_price and platform=='SeatGeek' else None,'buyer_cost_per_ticket_reference':est,'cost_status':'平均费率估算' if platform=='SeatGeek' else '用户确认含费的地图报价','cost_low_fee_scenario':round(price*(1+fee_low),2) if known_price and platform=='SeatGeek' else price,'cost_high_fee_scenario':round(price*(1+fee_high),2) if known_price and platform=='SeatGeek' else price,'excluded_displayed_over_1000':exclude,'normalized_cost_over_1000':est is not None and est>1000,'ordinary100_section':ordinary,'model_row_domain':row_ok,'event_accepted_for_comparison':event_ok,'quote_reference_eligible':known_price and not exclude and ordinary and event_ok,'seat_reference_eligible':known_price and not exclude and row_ok and event_ok,'selected_quantity':None,'inventory_quantity':None,'seat_number':None,'listing_id':None,'price_unit_status':'按每张地图报价暂记，订单数量未显示','exact_capture_time_utc':None,'zip_member_modified_local':time_zip,'zip_time_zone':'未记录；仅文件元数据，不等同采集时间','received_at_utc':asof.isoformat(),'reference_asof_utc':asof.isoformat(),'source_file':rel,'source_sha256':image['sha256'],'notes':note,'review_status':'；'.join(status),'model_estimate_is_net_proceeds':False,'paper_trade_entered':False,'snapshot_batch':image['snapshot_batch'],'original_folder_name':folder,'raw_file_relativepath':image['raw_file_relativepath'],'snapshot_role':'日期待核对，历史隔离' if not event_ok else ('重拍报价快照' if is_update else '原始报价快照'),'date_assignment_evidence':'用户明确确认新建文件夹为1007' if folder=='新建文件夹' else '用户文件夹与本次说明；截图未展示场次标题'}
  rows.append(rowdict)
  rowdict['excluded_by_price_policy']=exclude_policy
  rowdict['quote_reference_eligible']=rowdict['quote_reference_eligible'] and not exclude_policy
  rowdict['seat_reference_eligible']=rowdict['seat_reference_eligible'] and not exclude_policy
d=pd.DataFrame(rows)
assert len(d)==1118 and d.observation_id.is_unique
assert not d.excluded_displayed_over_1000[d.displayed_price_usd.eq(1000)].any()
# Combinations collapse repeated visible values only when row and event are known.
# They do not identify unique listings, and row-unknown records are never auto-dropped.
d['quote_combination_key']=d.observation_id
mask=d.row.notna()&d.event_date_folder.notna()&d.displayed_price_usd.notna()
d.loc[mask,'quote_combination_key']=d.loc[mask,['snapshot_batch','platform','event_date_folder','section_label','row','displayed_price_usd']].astype(str).agg('|'.join,axis=1)
d['same_seat_price_observation_count']=d.groupby('quote_combination_key').observation_id.transform('size')
d['repeated_seat_price_combination']=mask&d.duplicated('quote_combination_key',keep='first')

# Frozen price references for known, eligible seat map observations only.
model=json.loads((INPUT/'frozen_forecast_model.json').read_text());origin=pd.Timestamp(model['origin_utc'])
assert digest(INPUT/'model_v1_frozen.py')==model['v1_source_sha256']
ns={'pd':pd,'np':np,'events':model['events'],'sections':model['sections'],'quantities':model['quantities']}
nodes=[n for n in ast.parse((INPUT/'model_v1_frozen.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='design']
exec(compile(ast.Module(body=nodes,type_ignores=[]),'model_v1_frozen.py','exec'),ns)
coeff=model['coefficients'];ix=d.index[d.seat_reference_eligible]
frame=pd.DataFrame({'event':d.loc[ix,'event_date_folder'],'s':d.loc[ix,'section_numeric'],'r':d.loc[ix,'row'],'ts':pd.to_datetime(d.loc[ix,'reference_asof_utc'],utc=True)})
frame['event_start']=pd.to_datetime(frame.event+' 20:00').dt.tz_localize('America/New_York').dt.tz_convert('UTC')
for q in ['1','2']:
 frame['q']=q
 X,names,_=ns['design'](frame,origin);assert names==list(coeff)
 d.loc[ix,'model_sh_base_price_qty'+q+'_scenario']=np.exp(X@np.array([coeff[k] for k in names]))
d['model_data_cutoff_utc']=origin.isoformat()
d['model_comparison_note']='模型为sh来源费用前价格；地图为含费成本；不可直接相减当利润；数量1/2为情景，不是已知购买数量'

cols=['included_in_research','source','Section','Row','valid_prestart','price_usd_base','observed_at_utc','event_date','qty_group','record_key']
h=pd.read_csv(INPUT/'Harry_current_sales_20260929.csv',usecols=cols,low_memory=False)
h['s']=pd.to_numeric(h.Section,errors='coerce');h['r']=pd.to_numeric(h.Row,errors='coerce');h['ts']=pd.to_datetime(h.observed_at_utc,utc=True)
h=h[h.included_in_research & h.source.eq('sh') & h.valid_prestart & h.price_usd_base.gt(0) & h.event_date.isin(d.event_date_folder.dropna()) & h.ts.lt(origin)].copy()
h['band']=pd.cut(h.r,[2,6,10,15,22],labels=['3-6','7-10','11-15','16-22'])
for i,x in d.loc[ix].iterrows():
 band=pd.cut(pd.Series([x.row]),[2,6,10,15,22],labels=['3-6','7-10','11-15','16-22']).iloc[0]
 recent=h[h.event_date.eq(x.event_date_folder)&h.s.eq(x.section_numeric)&h.band.eq(band)&h.ts.ge(pd.Timestamp(x.reference_asof_utc)-pd.Timedelta(days=7))]
 d.loc[i,'historical_same_event_section_rowband_7d_n']=len(recent)
 d.loc[i,'historical_7d_median_base_min5']=recent.price_usd_base.median() if len(recent)>=5 else np.nan

# Marker counts describe this partial, overlapping sample; never inventory or trade counts.
audit={'images':len(meta),'image_hash_duplicates':len(meta)-len({x['sha256'] for x in meta}),'marker_observations':len(d),'readable_prices':int(d.displayed_price_usd.notna().sum()),'occluded_prices':int(d.displayed_price_usd.isna().sum()),'price_excluded_markers':int(d.excluded_displayed_over_1000.sum()),'fee_rate_mean':fee_rate,'fee_rate_low':fee_low,'fee_rate_high':fee_high,'fee_calibration_unique_combinations':16,'fee_rate_method':'simple mean of fee/base across 16 distinct observed seat/price combinations; duplicate 117 Row12 observation collapsed; discounts separate','ordinary100_observations':int(d.ordinary100_section.sum()),'ordinary100_with_row_reading':int((d.ordinary100_section&d.row.notna()).sum()),'ordinary100_missing_row':int((d.ordinary100_section&d.row.isna()).sum()),'repeated_known_seat_price_observations':int(d.repeated_seat_price_combination.sum()),'seat_references_after_combination_dedup':int((d.seat_reference_eligible&~d.repeated_seat_price_combination).sum()),'fee_estimated_crosses1000_displayed_not_over1000':int((d.platform.eq('SeatGeek')&~d.excluded_displayed_over_1000&d.normalized_cost_over_1000).sum()),'seatgeek_unknown_date_images':4,'seatgeek_crossdate_review_images':10,'capture_time_known':0,'quantity_known':0,'listing_id_known':0,'historical_model_refit':False,'screenshots_added_to_sales_training':False,'paper_trades_entered':0,'reference_asof_utc':ASOF.isoformat(),'model_data_cutoff_utc':origin.isoformat(),'model_sha256':digest(INPUT/'frozen_forecast_model.json'),'input_sales_sha256':digest(INPUT/'Harry_current_sales_20260929.csv'),'manual_extraction_sha256':digest(ROOT/'work/manual_extract.py')}
csvsave(d,'all_quote_observations.csv')
csvsave(d[d.excluded_by_price_policy],'excluded_price_markers.csv')
csvsave(d[d.quote_reference_eligible],'section_quote_references.csv')
csvsave(d[d.snapshot_batch.eq('原始批次')&~d.event_accepted_for_comparison],'quarantined_old_seatgeek_quotes.csv')
csvsave(d[d.snapshot_batch.eq('重拍批次')],'new_seatgeek_quote_observations.csv')
csvsave(d[d.snapshot_batch.eq('重拍批次')&d.quote_reference_eligible],'new_seatgeek_section_references.csv')
seats=d[d.seat_reference_eligible&~d.repeated_seat_price_combination].copy()
csvsave(seats,'seat_quote_references.csv')
csvsave(d[~d.event_accepted_for_comparison|d.displayed_price_usd.isna()|(d.ordinary100_section&d.row.isna())],'needs_review.csv')
summary=d.groupby(['platform','event_date_folder'],dropna=False).agg(image_count=('image_id','nunique'),marker_observations=('observation_id','size'),readable_prices=('displayed_price_usd','count'),excluded_price_markers=('excluded_displayed_over_1000','sum'),section_reference_observations=('quote_reference_eligible','sum'),seat_reference_observations=('seat_reference_eligible','sum')).reset_index()
csvsave(summary,'platform_event_summary.csv')
image_manifest=[]
for m in meta:
 p=ROOT/m['raw_file_relativepath'];assert digest(p)==m['sha256']
 sub=d[d.image_id.eq(m['image_id'])]
 image_manifest.append({**m,'platform':sub.platform.iloc[0],'event_date_folder':sub.event_date_folder.iloc[0],'event_identity_status':sub.event_identity_status.iloc[0],'markers':len(sub),'prices_occluded':int(sub.displayed_price_usd.isna().sum()),'rows_unknown_ordinary100':int((sub.ordinary100_section&sub.row.isna()).sum()),'zip_member_modified_local':zip_times.get(m['path']),'bytes':p.stat().st_size})
csvsave(pd.DataFrame(image_manifest),'image_manifest.csv')
cross=[]
for key,g in seats.groupby(['event_date_folder','section_numeric','row']):
 if g.platform.nunique()<2:continue
 mins=g.groupby('platform').buyer_cost_per_ticket_reference.min().to_dict()
 cross.append({'event':key[0],'section':int(key[1]),'row':int(key[2]),**mins,'note':'同场同Section同Row地图观察；非同一挂牌；数量未知；采集时点不同时；不等于可执行价差'})
csvsave(pd.DataFrame(cross),'cross_platform_same_row_references.csv')
audit['cross_platform_same_row_cells']=len(cross)
audit['excluded_total_including_estimated_fee_crossings']=int(d.excluded_by_price_policy.sum())
# Cross-date overlap is a quality flag, not proof the two folders are identical events.
overlap={}
sg=d[d.platform.eq('SeatGeek')&d.snapshot_batch.eq('原始批次')&d.ordinary100_section&d.displayed_price_usd.notna()]
for ev in ['2026-09-30','2026-10-02']:
 overlap[ev]=set(map(tuple,sg[sg.event_date_folder.eq(ev)][['section_label','displayed_price_usd']].drop_duplicates().to_numpy()))
both=overlap['2026-09-30']&overlap['2026-10-02']
audit['seatgeek_0930_distinct_section_price_pairs']=len(overlap['2026-09-30'])
audit['seatgeek_1002_distinct_section_price_pairs']=len(overlap['2026-10-02'])
audit['seatgeek_shared_section_price_pairs_between_folders']=len(both)
csvsave(pd.DataFrame(sorted(both),columns=['section','displayed_price_usd']),'seatgeek_crossdate_overlap.csv')
# Match exact Section/displayed-price pairs to assess identity, not returns.
# Original uncertain dates remain quarantined; overlap is evidence, not proof.
pair_sets={}
for (batch,event),g in d[d.platform.eq('SeatGeek')&d.ordinary100_section&d.displayed_price_usd.notna()].groupby(['snapshot_batch','event_date_folder']):
 pair_sets[(batch,event)]=set(map(tuple,g[['section_label','displayed_price_usd']].drop_duplicates().to_numpy()))
evidence=[]
for oldevent in ['2026-09-30','2026-10-02']:
 for newevent in ['2026-09-30','2026-10-02']:
  a=pair_sets[('原始批次',oldevent)];b=pair_sets[('重拍批次',newevent)]
  evidence.append({'old_folder_date':oldevent,'new_folder_date':newevent,'old_pairs':len(a),'new_pairs':len(b),'shared_pairs':len(a&b),'old_pair_match_fraction':len(a&b)/len(a),'note':'精确Section+展示价匹配；包括高价用于识别；不是收益或成交证据'})
csvsave(pd.DataFrame(evidence),'seatgeek_date_identity_evidence.csv')
batch_summary=d.groupby(['snapshot_batch','platform','event_date_folder'],dropna=False).agg(images=('image_id','nunique'),observations=('observation_id','size'),raw_over_1000=('excluded_displayed_over_1000','sum'),price_policy_excluded=('excluded_by_price_policy','sum'),section_references=('quote_reference_eligible','sum')).reset_index()
csvsave(batch_summary,'snapshot_batch_summary.csv')
audit.update({'seatgeek_unknown_date_images':0,'seatgeek_crossdate_review_images':10,'seatgeek_1007_confirmed_images':4,'new_screenshots':len(update_meta),'new_marker_observations':int(d.snapshot_batch.eq('重拍批次').sum()),'date_identity_evidence':evidence,'new_snapshot_reference_asof_utc':UPDATE_ASOF.isoformat(),'manual_update_extraction_sha256':digest(ROOT/'work/manual_extract_update.py'),'old_0930_used_as_current':False,'snapshot_batches_kept_separate':True,'listing_disappearance_assumed_sold':False})
textsave(OUT/'audit.json',json.dumps(cleanjson(audit),ensure_ascii=False,indent=2))
payload={'audit':audit,'observations':d.replace({np.nan:None}).to_dict('records'),'summary':summary.replace({np.nan:None}).to_dict('records'),'images':image_manifest,'fees':fee.replace({np.nan:None}).to_dict('records'),'cross_platform':cross}
textsave(ROOT/'work/workbook_data.json',json.dumps(cleanjson(payload),ensure_ascii=False,indent=2))
print(json.dumps(cleanjson(audit),ensure_ascii=False,indent=2))
print(summary.to_string(index=False))
print('CROSS_PLATFORM',json.dumps(cross[:8],ensure_ascii=False))

from pathlib import Path
import ast, hashlib, json, os, re, shutil, zipfile
from html import escape
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent/'msg_update_20260929'
UPLOAD=ROOT.parent/'upload'
OUT=ROOT/'outputs'; RAW=ROOT/'raw'; INPUT=ROOT/'input'
for p in [OUT,RAW,INPUT]: p.mkdir(exist_ok=True)
ASOF=pd.Timestamp('2026-09-29T23:16:09Z')
EXIT=pd.Timestamp('2026-09-30 18:00',tz='America/New_York').tz_convert('UTC')
START=pd.Timestamp('2026-09-30 20:00',tz='America/New_York').tz_convert('UTC')
MAPS=json.loads((ROOT/'map_annotations.json').read_text())
CUTOFF=float(MAPS['cutoff_rule']['threshold_usd'])
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save_csv(f,name):
    p=OUT/name; tmp=p.with_suffix(p.suffix+'.pending')
    f.to_csv(tmp,index=False); os.replace(tmp,p)
def write_text(p,s):
    tmp=p.with_suffix(p.suffix+'.pending'); tmp.write_text(s,encoding='utf-8'); os.replace(tmp,p)

obs=json.loads((ROOT/'observations.json').read_text())
manifest=[]
for i,x in enumerate(obs):
    x['observation_id']=f'Q{i+1:02d}'
    dest=RAW/x['file'];src=dest if dest.exists() else UPLOAD/x['file']
    if src!=dest:shutil.copyfile(src,dest)
    assert digest(src)==digest(dest)
    manifest.append({'file':x['file'],'sha256':digest(src),'bytes':src.stat().st_size,'role':'checkout observation'})
    x['platform']='SeatGeek';x['event_date']='2026-09-30';x['event']='Harry Styles with Jamie XX';x['venue']='Madison Square Garden'
    x['source_sha256']=digest(src)
    x['listing_id']=None
    x['inventory_quantity']=None # The selected quantity is not total inventory.
    x['restrictions_status']='not fully verified from cropped checkout screenshot'
    x['checkout_stage']='1 of 2; not purchased'
    x['received_at_utc']='2026-09-29T23:16:09Z' if x['batch']=='current' else '2026-09-29T23:07:18Z'
    m=re.search(r'2026-09-29-(\d{2})(\d{2})(\d{2})',x['file'])
    x['capture_time_filename']=f'2026-09-29 {m[1]}:{m[2]}:{m[3]}' if m else None
    x['capture_time_utc_assuming_chicago']=str(pd.Timestamp(x['capture_time_filename'],tz='America/Chicago').tz_convert('UTC')) if m else None
    x['capture_time_note']='Filename clock; America/Chicago assumed, not screenshot-verified' if m else 'Exact capture timestamp unavailable; received timestamp is only an upper bound'
    x['fee_rate']=x['fee']/x['base']
    x['reconciliation_error']=round(x['base']+x['fee']-x['discount']-x['total'],2)
    assert x['reconciliation_error']==0
for name in ['02-105r2.jpg','04-1152.jpg','05-117row12.jpg']:
    src=RAW/name if (RAW/name).exists() else UPLOAD/name
    if src!=RAW/name:shutil.copyfile(src,RAW/name)
    manifest.append({'file':name,'sha256':digest(src),'bytes':src.stat().st_size,'role':'supporting listing detail'})
f=pd.DataFrame(obs)
assert len(f)==17 and len(f[f.batch.eq('current')])==14
save_csv(f,'quote_observations.csv')
map_registry=[];map_exclusions=[];stub_rows=[]
for item in MAPS['screenshots']:
    dst=RAW/item['file'];src=dst if dst.exists() else UPLOAD/item['file']
    if src!=dst:shutil.copyfile(src,dst)
    manifest.append({'file':item['file'],'sha256':digest(dst),'bytes':dst.stat().st_size,'role':item['platform']+' '+item['kind']})
    map_registry.append({'file':item['file'],'platform':item['platform'],'identity_basis':item['identity_basis'],'kind':item['kind'],'visible_excluded_marker_count':len(item['excluded_visible_labels']),'notes':item['notes']})
    for j,price in enumerate(item['excluded_visible_labels'],1):
        assert price>CUTOFF
        map_exclusions.append({'file':item['file'],'platform':item['platform'],'marker_number_within_file':j,'displayed_price':price,'reason':'user cutoff: displayed price > 1000','listing_id':None,'ticket_count':None,'row':None,'fee_basis':'not established for this individual map label','not_a_ticket_count':True})
    if 'section_prices' in item:
        for section,price in item['section_prices'].items():
            stub_rows.append({'file':item['file'],'platform':'StubHub','section':int(section),'displayed_price':price,'row':None,'selected_quantity':None,'fee_basis':'not visible','event_date_context':'2026-09-30 from conversation; cropped map does not independently confirm','excluded_above_1000':price>CUTOFF,'ready_for_matched_comparison':False})
save_csv(pd.DataFrame(manifest),'source_manifest.csv')
save_csv(pd.DataFrame(map_registry),'screenshot_platform_registry.csv')
save_csv(pd.DataFrame(map_exclusions),'excluded_map_price_markers.csv')
save_csv(pd.DataFrame(stub_rows),'StubHub_section_map_prices.csv')
save_csv(pd.DataFrame(stub_rows).query('not excluded_above_1000'),'StubHub_section_map_prices_under_cap.csv')
key=['platform','event_date','section','row','seat','quantity','base','fee','discount','total']
f['combination_key']=f[key].fillna('unknown').astype(str).agg('|'.join,axis=1)
latest=f.drop_duplicates('combination_key',keep='last').copy()
latest['observation_count']=latest.combination_key.map(f.groupby('combination_key').size())
latest['all_observation_ids']=latest.combination_key.map(f.groupby('combination_key').observation_id.agg(','.join))
latest['all_source_files']=latest.combination_key.map(f.groupby('combination_key').file.agg(';'.join))
latest['combination_not_listing_identity']=True
latest=latest.sort_values(['section','row']).reset_index(drop=True)
assert len(latest)==16

for source,dest in [(BASE/'outputs/frozen_forecast_model.json',INPUT/'frozen_forecast_model.json'),(BASE/'model_v1_frozen.py',INPUT/'model_v1_frozen.py'),(BASE/'outputs/Harry_current_sales_20260929.csv',INPUT/'Harry_current_sales_20260929.csv'),(BASE/'outputs/forecast_grid_4_events.csv',INPUT/'forecast_grid_4_events.csv')]:
    if not dest.exists():shutil.copyfile(source,dest)
model_path=INPUT/'frozen_forecast_model.json'
model=json.loads(model_path.read_text())
origin=pd.Timestamp(model['origin_utc'])
v1=INPUT/'model_v1_frozen.py'
assert digest(v1)==model['v1_source_sha256']
ns={'pd':pd,'np':np,'events':model['events'],'sections':model['sections'],'quantities':model['quantities']}
node=ast.parse(v1.read_text());nodes=[n for n in node.body if isinstance(n,ast.FunctionDef) and n.name=='design']
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(v1),'exec'),ns)
coef=model['coefficients']

master=INPUT/'Harry_current_sales_20260929.csv'
cols=['included_in_research','source','Section','Row','valid_prestart','price_usd_base','observed_at_utc','event_start_utc','event_date','qty_group','record_key']
d=pd.read_csv(master,usecols=cols,low_memory=False)
d=d[d.included_in_research & d.source.eq('sh') & d.valid_prestart & d.price_usd_base.gt(0)].copy()
d['s']=pd.to_numeric(d.Section,errors='coerce');d['r']=pd.to_numeric(d.Row,errors='coerce')
d=d[d.s.between(101,120)&d.s.eq(d.s.round())&d.r.between(3,22)&d.r.eq(d.r.round())].copy()
d['ts']=pd.to_datetime(d.observed_at_utc,utc=True);d['event']=d.event_date.astype(str);d['q']=d.qty_group.astype(str);d['price']=d.price_usd_base
d['band']=pd.cut(d.r,[2,6,10,15,22],labels=['3-6','7-10','11-15','16-22']).astype(str)
train=d[d.ts.lt(origin)&d.ts.ge(origin-pd.Timedelta(days=90))]
assert len(train)==9872
# Comparison evidence is limited to the event and sources already in the frozen model.
history=train[train.event.eq('2026-09-30')].copy()
save_csv(history,'comparison_history.csv')
recent72=history[history.ts.ge(origin-pd.Timedelta(hours=72))]
recent7=history[history.ts.ge(origin-pd.Timedelta(days=7))]

latest['in_model_domain']=latest.row.between(3,22)
latest['row_band']=pd.cut(latest.row,[2,6,10,15,22],labels=['3-6','7-10','11-15','16-22']).astype('string')
latest['model_asof_utc']=str(ASOF);latest['model_exit_utc']=str(EXIT)
latest['model_data_cutoff_utc']=str(origin);latest['model_source']='sh'
latest['actual_seller_fee_rate']=np.nan
latest['estimated_net_exit_proceeds']=np.nan
latest['max_buy_price']=np.nan
latest['paper_trade_quantity']=0
latest['decision']='No paper entry: cross-platform price/payout mapping unverified'
for label,t in [('now',ASOF),('exit',EXIT)]:
    ix=latest.index[latest.in_model_domain]
    frame=pd.DataFrame({'event':'2026-09-30','event_start':START,'ts':t,'s':latest.loc[ix,'section'],'r':latest.loc[ix,'row'],'q':'1'})
    X,names,_=ns['design'](frame,origin)
    assert names==list(coef)
    latest.loc[ix,'model_sh_recorded_price_'+label]=np.exp(X@np.array([coef[k] for k in names]))
for i,x in latest.iterrows():
    if not x.in_model_domain:
        latest.loc[i,'decision']='Outside model domain: Row 2; no extrapolated valuation'
        continue
    h72=recent72[recent72.s.eq(x.section)&recent72.band.eq(x.row_band)]
    h7=recent7[recent7.s.eq(x.section)&recent7.band.eq(x.row_band)]
    h72q=h72[h72.q.eq('1')]
    latest.loc[i,'comparable_n72_any_quantity']=len(h72)
    latest.loc[i,'comparable_n72_quantity1']=len(h72q)
    latest.loc[i,'comparable_n7_any_quantity']=len(h7)
    latest.loc[i,'strict72_median_min5']=h72.price.median() if len(h72)>=5 else np.nan
    latest.loc[i,'strict72_median_qty1_min5']=h72q.price.median() if len(h72q)>=5 else np.nan
    # A descriptive cross-source diagnostic, not an executable return or fee-normalized spread.
    latest.loc[i,'seatgeek_base_over_model_sh_pct_unadjusted']=100*(x.base/latest.loc[i,'model_sh_recorded_price_now']-1)
latest['excluded_above_1000']=latest.total.gt(CUTOFF)
latest['exclusion_reason']=np.where(latest.excluded_above_1000,'User rule: current per-ticket checkout total > $1000','')
latest.loc[latest.excluded_above_1000,'decision']='Excluded by user price cap; raw observation retained'
save_csv(latest,'all_quote_combinations.csv')
save_csv(latest[latest.excluded_above_1000],'excluded_quotes.csv')
save_csv(latest[~latest.excluded_above_1000],'candidate_comparison.csv')

# Independent numerical cross-check against the earlier frozen grid, without refitting.
grid=pd.read_csv(INPUT/'forecast_grid_4_events.csv')
g=grid[(grid.event=='2026-09-30')&(grid.s==107)&(grid.r==15)&(grid.forecast=='snapshot')].iloc[0]
check=pd.DataFrame([{'event':'2026-09-30','event_start':START,'ts':origin,'s':107,'r':15,'q':'2'}])
X,names,_=ns['design'](check,origin);check_price=float(np.exp(X@np.array([coef[k] for k in names]))[0])
assert abs(check_price-g.model_price_usd_base)<1e-8
assert latest.loc[latest.in_model_domain,'model_sh_recorded_price_now'].gt(0).all()

audit={'new_screenshots':14,'checkout_observations_including_previous':17,'distinct_observed_seat_price_combinations':16,'model_eligible_combinations':int(latest.in_model_domain.sum()),'sections':int(latest.section.nunique()),'new_fee_rate_min':float(f[f.batch.eq('current')].fee_rate.min()),'new_fee_rate_max':float(f[f.batch.eq('current')].fee_rate.max()),'all_combinations_fee_rate_min':float(latest.fee_rate.min()),'all_combinations_fee_rate_max':float(latest.fee_rate.max()),'new_total_min':float(f[f.batch.eq('current')].total.min()),'new_total_max':float(f[f.batch.eq('current')].total.max()),'reconciliation_failures':int(f.reconciliation_error.ne(0).sum()),'comparison_asof_utc':str(ASOF),'comparison_asof_new_york':str(ASOF.tz_convert('America/New_York')),'model_data_cutoff_utc':str(origin),'model_source_sha256':digest(v1),'model_json_sha256':digest(model_path),'master_sha256':digest(master),'comparison_history_n':len(history),'strict72_min5_coverage':int(latest.strict72_median_min5.notna().sum()),'strict72_qty1_min5_coverage':int(latest.strict72_median_qty1_min5.notna().sum()),'model_refit':False,'fixed_grid_reproduction_passed':True,'quotes_added_to_sales_training':False,'paper_trades_entered':0,'sampling':'User-selected partial snapshot after subjective omission of expensive apparent multi-seat/row listings. Omitted count, prices, true inventory and intent unknown. Not verified lowest-price sampling.','capture_timezone':'Filename times assumed America/Chicago; missing filename times are not imputed as exact capture times.','notes':'17 observations -> 16 seat/price combinations, not 16 confirmed listing IDs. All selected quantities are 1; inventory quantities unknown. No claim of seller identity, intent, non-sale or fake ask.'}
audit.update({'cutoff_rule':MAPS['cutoff_rule'],'excluded_checkout_combinations':int(latest.excluded_above_1000.sum()),'active_checkout_candidates':int((~latest.excluded_above_1000).sum()),'map_excluded_price_markers_not_tickets':len(map_exclusions),'stubhub_section_labels':len(stub_rows),'stubhub_retained_section_labels':int((~pd.DataFrame(stub_rows).excluded_above_1000).sum()),'historical_sales_cut_by_asking_price_rule':False,'platforms_confirmed':['SeatGeek','TickPick','Gametime','Ticketmaster','StubHub']})
write_text(OUT/'audit.json',json.dumps(audit,ensure_ascii=False,indent=2))

def money(x):return '—' if pd.isna(x) else f'${x:,.2f}'
rows=[]
for x in latest[~latest.excluded_above_1000].itertuples():
    n='—' if pd.isna(getattr(x,'comparable_n72_quantity1',np.nan)) else str(int(x.comparable_n72_quantity1))
    note='前排，模型不估值' if not x.in_model_domain else '来源差异待核对'
    if x.section==109 and x.row==21:note+='；卖家备注被截断'
    rows.append('<tr>'+''.join('<td>'+escape(str(v))+'</td>' for v in [f'{x.section} / {x.row}',money(x.base),money(x.fee),money(x.discount),money(x.total),money(x.model_sh_recorded_price_now),money(x.model_sh_recorded_price_exit),n,note])+'</tr>')
detail=[]
for x in f.itertuples():
    detail.append('<tr>'+''.join('<td>'+escape(str(v))+'</td>' for v in [x.observation_id,x.file,f'{x.section}/{x.row}',x.quantity,money(x.total),x.capture_time_filename or '无精确时间',x.received_at_utc])+'</tr>')
html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Harry MSG 在售报价核对</title><style>
body{font-family:Arial,"Noto Sans CJK SC",sans-serif;background:#f5f7fa;color:#182535;margin:0;line-height:1.65}main{max-width:1280px;margin:32px auto;background:white;padding:36px;border-radius:12px}h1{font-size:27px;margin:0 0 12px}h2{font-size:21px;margin-top:32px}.lead{font-size:18px}.note{background:#fff5dc;border-left:4px solid #d7a237;padding:14px 18px}.ok{background:#eaf3f6;padding:14px 18px}.scroll{overflow:auto}table{width:100%;border-collapse:collapse;font-size:13px}th{text-align:left;background:#17394a;color:white;padding:10px;white-space:nowrap}td{padding:9px;border-bottom:1px solid #dde4e9}tr:nth-child(even){background:#f7fafc}.small{font-size:13px;color:#516273}code{background:#f1f4f7;padding:2px 4px}a{color:#175e7b}li{margin:8px 0}@media print{body{background:white}main{margin:0;padding:12px}th{color:black;background:#ddd}tr{break-inside:avoid}}
</style><main><h1>Harry Styles · MSG · 9 月 30 日在售报价核对</h1>
<p class="lead">SeatGeek 结算截图共 17 条观察、16 个不同座位／报价组合，全部选择购买 1 张，覆盖 12 个 Section。按用户最新规则排除单张含费成本严格大于 $1,000 的报价后，保留 15 个候选组合。另附 TickPick、Gametime、Ticketmaster 与 StubHub 的截图标注。</p>
<p class="ok">本轮结论：买入成本已经可记录；卖出净收入尚不能可靠计算，因此本轮模拟买入数量为 0。这里的 0 表示没有建立交易，不代表证明这些票一定无法盈利。</p>
<h2>高价票如何处理</h2><p>用户在采集时排除了一部分看起来覆盖整排、报价极高的票。该事实记录为采样限制，未记录的票数和价格保持未知。仅凭排面高亮与高价，不能确认整排库存属于一个卖家，也不能确认锁仓意图或最终无人购买。</p>
<p>用户在纽约时间 9/29 19:32 明确指定：本轮所有在售截图中，展示价格严格大于 $1,000 的票排除出候选分析；等于 $1,000 保留。结算截图使用明确的单张含费合计，地图使用可见展示价，未知费用不作换算。原图和排除记录全部保留。这是用户设定的样本范围，不代表统计上已证明报价错误或不会成交；历史销售训练数据不套用这一在售报价筛选规则。</p>
<p>SeatGeek 105 区 Row 2：基础价 $894，含费总价 $1,021.51，按含费成本排除。其原始结算记录和显示为 $1,022 的详情图都保留。此前用户未截图的高价票仍只有排除说明，没有虚构票数或价格。</p>
<h2>费用核对</h2><p>17 条结算记录均满足：基础价 + 买家手续费 − 折扣 = 当前结算合计。117 区 Row 12 的 $9.11 折扣单独保留，不视为手续费下降。所有截图停在结算第 1 步，未购买；未显示的后续税费或附加项仍需最终核实。</p>
<p>新截图手续费占基础价的比例为 NEWMIN%–NEWMAX%；连同上一批，范围为 ALLMIN%–ALLMAX%。不能由这些观察推导一个全平台固定费率。买家手续费与未来卖家手续费是不同字段。</p>
<h2>逐组价格参考</h2><p>报价来自 SeatGeek；模型参考来自 SeatData 的 <code>sh</code> 历史记录。模型按单张数量 <code>q=1</code> 重新代入已有系数，没有重新拟合，也没有把在售报价混入成交训练集。</p>
<p class="note">SeatData 官方 FAQ 已确认页面展示价不含手续费，但两个平台基础价的市场差异和卖家到账映射尚未校准。表中模型数值不是 SeatGeek 建议挂牌价、卖出到账金额或保证成交价，不直接计算利润。119 区 Row 16 的 9/28 单张历史记录为 $270，而当前模型约 $194、SeatGeek 基础报价 $288，因此必须检查模型低估的可能，不能只归因于平台。普通模型只覆盖 Row 3–22。</p>
<p class="small">统一估值时间：纽约 9/29 19:16:09。未来参考时点：纽约 9/30 18:00，距计划开场 2 小时。模型数据截止：纽约 9/29 18:36:39。72 小时样本数以此数据截止点计算，匹配场次、Section、排数组别及数量 1。无样本不等于无需求。</p>
<div class="scroll"><table><thead><tr><th>Section / Row</th><th>基础价</th><th>买家费</th><th>折扣</th><th>当前合计</th><th>sh 当前模型参考</th><th>sh 明日18时参考</th><th>72h同组单张记录</th><th>说明</th></tr></thead><tbody>ROWS</tbody></table></div>
<p>15 个模型范围内组合中，72 小时同场次、Section、排数组别且至少 5 条记录的覆盖为 COVERANY 个；再限定数量 1 后为 COVERONE 个。因此不能把薄样本均价当成稳定退出价格。</p>
<h2>下一步交易规则</h2><ol><li>先核对 SeatData <code>Price</code> 与拟卖出平台的基础价、卖家到账口径。SeatGeek 买入明细已知，无法自动补足另一端的净收入。</li><li>在确认映射后，计算：保守卖出净收入 − 含费买入成本 − 其他实际费用。估值误差、售出概率、转售交付时间和未售出票到期损失都需考虑。</li><li>将能满足条件的票填入固定的模拟交易记录，先记录判断再观察后续结果。拿不到足够证据时保留不交易，不能把后续相似座位成交强行当成本票已成交。</li></ol>
<p>不用为了本轮再补齐所有 Section。当前缺口主要是来源一致的可比价格、模型偏差及卖出净收入和交付条件。109 区 Row 21 的“卖家备注”正文被截掉，暂不视为限制条件已核实。</p>
<h2>记录与来源</h2><p>117 区 Row 12 在两批都出现，汇总为一个座位／报价组合，保留两次观察。没有 Listing ID，无法确认它们一定是同一挂牌。截图中的 ×1 是本次选择的购买张数，不是卖家剩余总库存。</p>
<p>文件名中的 18:11:25–18:14:20 暂按芝加哥时间解释，对应纽约 19:11:25–19:14:20；截图本身没有验证设备时区。11222.jpg 及上一批文件没有精确时间，上传时间仅作上界。</p>
<div class="scroll"><table><thead><tr><th>观察ID</th><th>截图</th><th>Section/Row</th><th>购买张数</th><th>合计</th><th>文件名时钟</th><th>接收时间UTC</th></tr></thead><tbody>DETAIL</tbody></table></div>
<p class="small">官方价格口径参考（此前已核对）：<a href="https://support.seatgeek.com/hc/en-us/articles/360036685293-Does-SeatGeek-charge-a-fee-to-buy-tickets">SeatGeek 含费展示说明</a>；<a href="https://docs.seatdata.io/docs/api/migrating-to-v1/">SeatData price / all_in_price 与来源字段</a>。具体金额依据用户截图。</p>
<p>截图提取及金额核对置信度：0.99。收益判断暂不成立，原因是跨平台映射、实际卖家费与成交概率尚未确定。</p></main></html>'''
for k,v in {'NEWMIN':f'{audit["new_fee_rate_min"]*100:.2f}','NEWMAX':f'{audit["new_fee_rate_max"]*100:.2f}','ALLMIN':f'{audit["all_combinations_fee_rate_min"]*100:.2f}','ALLMAX':f'{audit["all_combinations_fee_rate_max"]*100:.2f}','COVERANY':str(audit['strict72_min5_coverage']),'COVERONE':str(audit['strict72_qty1_min5_coverage']),'ROWS':''.join(rows),'DETAIL':''.join(detail)}.items():html=html.replace(k,v)
stubtable=''.join('<tr><td>'+str(x['section'])+'</td><td>'+money(x['displayed_price'])+'</td><td>'+('按价格规则排除' if x['excluded_above_1000'] else '保留为地图观察；待查 Row、数量和费用')+'</td></tr>' for x in stub_rows)
regtable=''.join('<tr><td>'+escape(x['platform'])+'</td><td>'+escape(x['file'])+'</td><td>'+str(x['visible_excluded_marker_count'])+'</td></tr>' for x in map_registry)
appendix='<h2>平台确认与地图筛选</h2><p>用户确认：18:28:53 的黑底地图为 TickPick，18:27:25 的彩色地图为 Gametime，18:30:28 的紫色分区地图为 StubHub。地图标签不等于可辨认的独立挂牌，也不代表整区全部库存价格；不能将下表排除标记数当作排除票数。</p><div class="scroll"><table><thead><tr><th>平台</th><th>截图</th><th>完整可读的 &gt;$1,000 标签数</th></tr></thead><tbody>'+regtable+'</tbody></table></div><p>StubHub 普通 100 Level 共 20 个清晰分区标签，其中 16 个在筛选范围内，展示价 $244–$464。103、108、110、120 的本次可见标签超过 $1,000；这是排除该报价，不是永远排除这四个 Section。另有 Disco $1,080 同样标记排除，且本身不在普通 100 Level 模型范围。</p><div class="scroll"><table><thead><tr><th>Section</th><th>地图展示价</th><th>状态</th></tr></thead><tbody>'+stubtable+'</tbody></table></div><p>Ticketmaster 截图为 117 区 Row 17、2 Tickets、Standard Admission、显示 $368，标注含费且税前。它保留为单独的官方票观察，每张/订单价格解释及明细仍待确认，不混入 SeatGeek 单张候选或历史销售训练集。</p>'
html=html.replace('<h2>记录与来源</h2>',appendix+'<h2>记录与来源</h2>')
write_text(OUT/'Harry_MSG_SeatGeek_quote_review.html',html)
readme='''Harry Styles MSG 2026-09-30 quote snapshot

Scope: 14 new checkout screenshots + 3 previous checkout observations. Supporting detail images retained. Each image is byte-preserved and hashed in source_manifest.csv.
observations.json is the manually verified transcription. quote_observations.csv preserves all 17 observations. candidate_comparison.csv combines only matching seat/price/quantity combinations, retaining every observation ID; this is not listing-ID deduplication.
User rule at 2026-09-29T23:32:26Z: exclude asking-price screenshots above $1000; exactly $1000 is retained. All original observations remain in quote_observations.csv and all_quote_combinations.csv. candidate_comparison.csv now contains 15 combinations after excluding the $1021.51 Section 105 Row 2 checkout quote. Map exclusions are price markers, not counts of tickets or proven unique listings. map_annotations.json defines platform provenance and visible-price exclusions. StubHub map observations are separate from matched seat/quantity candidates. The rule does not filter historical sales training data.
User also omitted some high-priced apparent row listings before submission; quantity and values are unknown. This is not a complete order book, random sample or verified set of minimum asks.
The model is frozen at the earlier data snapshot. Only its design function is reused, by AST extraction; top-level model training is not executed. q=1 is used. Row 2 receives no prediction. Comparison history comes from the original accepted sh sales; quotes are never added to it.
Model estimates and SeatGeek base prices have an unverified cross-platform mapping. No executable edge, net proceeds, maximum buy price or profitability claim is produced. All paper_trade_quantity values are 0, not completed trades.
The package includes the input master, model JSON, frozen design, earlier forecast-grid check, raw screenshots and observations. After extraction, run python3 analyze_quotes.py with pandas and numpy installed to reproduce the snapshot. Existing input files and raw screenshots take priority, so the prior project is not needed for a packaged rerun. No live browser, purchase or platform mutation is performed.
'''
write_text(ROOT/'README.txt',readme)
package=OUT/'Harry_MSG_SeatGeek_quote_package.zip';tmp=package.with_suffix('.zip.pending')
with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
    for p in [ROOT/'analyze_quotes.py',ROOT/'observations.json',ROOT/'map_annotations.json',ROOT/'README.txt']+sorted(RAW.glob('*'))+sorted(INPUT.glob('*'))+sorted(OUT.glob('*.csv'))+[OUT/'audit.json',OUT/'Harry_MSG_SeatGeek_quote_review.html']:
        z.write(p,p.relative_to(ROOT))
os.replace(tmp,package)
with zipfile.ZipFile(package) as z:
    assert z.testzip() is None
    for m in manifest:assert hashlib.sha256(z.read('raw/'+m['file'])).hexdigest()==m['sha256']
assert len(pd.read_csv(OUT/'quote_observations.csv'))==17
assert len(pd.read_csv(OUT/'candidate_comparison.csv'))==15
assert pd.read_csv(OUT/'candidate_comparison.csv').total.le(CUTOFF).all()
assert len(pd.read_csv(OUT/'all_quote_combinations.csv'))==16
assert pd.read_csv(OUT/'excluded_quotes.csv').total.gt(CUTOFF).all()
assert len(pd.read_csv(OUT/'StubHub_section_map_prices_under_cap.csv'))==16
print(json.dumps(audit,indent=2,ensure_ascii=False))
print(latest[['section','row','base','fee','discount','total','model_sh_recorded_price_now','model_sh_recorded_price_exit','comparable_n72_any_quantity','comparable_n72_quantity1']].round(2).to_string(index=False))
print('package_bytes',package.stat().st_size)

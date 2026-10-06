from pathlib import Path
import json,os,shutil,zipfile,hashlib
import pandas as pd

ROOT=Path(__file__).resolve().parent;O=ROOT/'outputs';R=ROOT/'raw'
A=json.loads((O/'audit.json').read_text());recon=pd.read_csv(O/'reconciliation.csv');quality=pd.read_csv(O/'new_file_quality_counts.csv');grid=pd.read_csv(O/'forecast_grid_4_events.csv');check=pd.read_csv(O/'previous_model_additional_period_metrics.csv')
def write(path,text):
 t=path.with_suffix(path.suffix+'.pending');t.write_text(text,encoding='utf-8');os.replace(t,path)
def table(df):return df.to_html(index=False,border=0,float_format=lambda x:f'{x:,.2f}',na_rep='不足5笔')
qt=quality.groupby('check')['count'].sum()
rt=recon[['event_date','new_rows','exact_overlap_records','new_distinct_records','new_after_prior_last_timestamp','backfilled_or_at_prior_last_timestamp','likely_revisions','old_unmatched_unresolved']].sort_values('event_date').rename(columns={'event_date':'演出日期','new_rows':'本次完整记录','exact_overlap_records':'与旧快照完全重叠','new_distinct_records':'此前未见记录','new_after_prior_last_timestamp':'旧快照最后时间之后','backfilled_or_at_prior_last_timestamp':'历史回补或同刻','likely_revisions':'疑似字段修订','old_unmatched_unresolved':'旧记录本次缺席'})
ref=grid[grid.s.eq(107)&grid.r.eq(15)].pivot(index='event',columns='forecast',values='model_price_usd_base').reset_index();support=grid[grid.s.eq(107)&grid.r.eq(15)&grid.forecast.eq('snapshot')][['event','comparable_n72_any_quantity','comparable_n72_same_quantity']];ref=ref.merge(support,on='event').rename(columns={'event':'演出日期','snapshot':'9/29 18:36估值 USD','next_day_18NY':'9/30 18:00预测 USD','comparable_n72_any_quantity':'72h同Section同排档记录','comparable_n72_same_quantity':'其中同数量记录'})
st=pd.read_csv(O/'event_update_summary.csv');st['last_record_NY']=pd.to_datetime(st.last_record_utc,utc=True).dt.tz_convert('America/New_York').dt.strftime('%m/%d %H:%M')
qview=pd.DataFrame([{'检查项':'同一新文件内完全相同行的额外条数','数量':int(qt.duplicate_extra_candidate)},{'检查项':'缺失Zone','数量':int(qt.missing_Zone)},{'检查项':'缺失Row（含各类座位）','数量':int(qt.missing_Row)},{'检查项':'普通100 Level中缺失Row','数量':int(qt.row100_missing)},{'检查项':'Qty=0：数量未知','数量':int(qt.qty_unknown)},{'检查项':'非法价格／非法时间／非法数量','数量':int(qt.price_invalid+qt.time_invalid+qt.qty_invalid)},{'检查项':'价格离群复核标记（不自动删除）','数量':int(qt.price_extreme_review)},{'检查项':'Qty大于20的复核标记','数量':int(qt.qty_large_review)}])
ch=check[['event_date','n','mae_usd','median_ape_pct']].rename(columns={'event_date':'场次','n':'记录数','mae_usd':'平均绝对误差 USD','median_ape_pct':'绝对百分比误差中位数 %'})
body=f'''<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Harry MSG 数据更新 2026-09-29</title><style>body{{font-family:system-ui,-apple-system,"Microsoft YaHei",sans-serif;color:#243b4d;background:#f3f6f9;margin:0}}main{{max-width:1180px;background:white;margin:auto;padding:35px}}h1{{font-size:30px}}h2{{font-size:22px;margin-top:32px}}p,li{{line-height:1.8}}.lead{{padding:18px;background:#eaf3f7;border-left:4px solid #257d99}}.note{{padding:17px;background:#fff6e2}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{padding:10px 8px;border-bottom:1px solid #dce4ec;text-align:right}}th{{background:#edf3f7}}th:first-child,td:first-child{{text-align:left}}.scroll{{overflow-x:auto}}code{{background:#f1f3f6;padding:2px 4px}}small{{color:#5d7181}}@media(max-width:700px){{main{{padding:20px}}}}</style><main>
<h1>Harry Styles · MSG · 四场数据更新</h1><p>接收时间：2026年9月29日纽约18:36:39／芝加哥17:36:39。文件未提供精确下载时间，最后一笔记录不等于下载时间或完整监控截止时间。</p>
<p class="lead">四份都是完整历史导出，共4,997条。完成快照衔接后，当前研究集为30场、38,570条记录。10月2日的新导出已纳入；原始文件、旧快照、修订候选及本次估值均保留。</p>
<h2>1. 新旧文件怎样衔接</h2><p>按七个原始字段标准化后进行多重集比较，保留重复次数，不使用集合去重。旧文件与新文件的完全重叠不是“重复交易”，而是多次下载同一历史。对这四场以新快照作为当前版本；旧文件保留在研究包，不将整个新文件追加到旧历史末尾。</p><div class="scroll">{table(rt)}</div>
<p>合计4,643条完全重叠、348条此前未见记录，其中344条发生在旧快照最后记录之后，4条为较早时间的回补或同刻新记录。另有6条疑似数量修订，2条旧记录在新快照中未出现。以上都是记录数，不是售出票数。</p>
<p><strong>10月2日身份核对：</strong>新1002与旧14-1002、15-0930这两个冲突文件各有1,201条相同记录；新0930与此前确认的sales_data.csv有1,276条相同记录，与那两个冲突文件没有相同记录。因此用户本次文件命名与历史指纹共同支持将新1002按10月2日纳入。导出没有演出ID，未声称做了平台ID级独立确认。旧两份冲突文件仍按原版本保留，不把它们再次相加。</p>
<p>以前接受的三场旧数据共3,448条，被本次对应的新快照替换，再加入10月2日：37,021 − 3,448 + 4,997 = 38,570。其他26场未重新采集，仍沿用旧快照。</p>
<h2>2. 清理与质量检查</h2><div class="scroll">{table(qview)}</div>
<p>缺失与复核标记可能重叠，不能直接相加当作坏数据总数。3条100 Level的WC记录保留为特殊座位，不混入普通Section。Price离群标记使用每个新文件的来源×座位大类内对数价格中位数与MAD，阈值4.5，组内至少20条；用于复核，不代表录入错误，也未改变v1模型的稳健损失规则。</p>
<p>Qty=0按未知处理。发现的6条修订都涉及数量，其中1003与1007有5条从未知变为具体数量，另1条10月2日GA记录从1变为2。没有Listing ID，故标为“疑似修订”，不宣称绝对是一笔交易。2条旧快照独有记录保留核查，原因未知。</p>
<p>时间继续按CSV标题EDT固定UTC−4解析，保留纽约本地时区的替代解释。{int(qt.winter_timezone_ambiguous)}条冬季/夏令时前记录存在1小时时区歧义标记；它们不在此次最近90天训练窗口中。开场时间继续沿用20:00纽约时间约定；距离开场精确保留，≤12小时归为12小时以内，不做向12小时取整。</p>
<h2>3. 估值模型更新</h2><p>v1的特征、损失函数、正则化强度、90天训练窗口和14天半衰期保持不变，使用当前快照重新估计系数。10月2日新增为已观察场次类别。模型全集13,873条，最近90天训练9,872条，固定sh、普通101–120、Row 3–22；特殊前两排仍不纳入。</p>
<p>下表统一为Section 107、Row 15、数量2条件下的<strong>每张基础价格</strong>。同数量不等于已确认连座。今天的估值与明天的预测均来自本次固定系数，没有用未来记录训练。</p><div class="scroll">{table(ref)}</div>
<p class="note">这四个参考座位都没有满足“过去72小时同场同Section同排档至少5条”的严格中位数条件，模型主要借用其他座位和历史信息。不能把这些数字当成可买报价、保证成交价或最高买价。实际Listing、手续费、税费、座位说明和库存仍缺失。</p>
<p>完整网格提供四场、20个Section、Row 6/10/15/20、数量2，在当前快照与9月30日18:00纽约时间两个时点的640个估计。未来时点所展示的历史中位数与样本数量均截止本次数据原点，未使用未来数据。</p>
<h2>4. 旧模型追加时间段检查</h2><p>保留上一版9月28日18:00纽约时间的系数，检查本次新导出中之后发生、且旧模型已有场次类别的69条普通席记录。10月2日旧模型没有场次类别，未拿错误的基准场次代替。</p><div class="scroll">{table(ch)}</div>
<p>这是追加时间段的回放检查，<strong>不是预测公开发布之后的前向验证</strong>：这些销售发生在本次文件上传前，上一版项目也已经研究过历史。与前次4,955条回放的样本构成不同，不能根据这69条误差更小就断言模型进步。</p>
<h2>5. 已冻结的下一轮检查</h2><p>固定当前数据原点与系数，预先约定验证窗口：<strong>纽约时间2026年9月30日00:00至10月1日00:00</strong>，只评分演出开始之前、sh来源、普通Section、Row3–22且数量字段有效的记录。9月30日那场在约定20:00开场后不再计入。后续数据到来时先用这一版本评分，再训练下一版；不能先重拟合再把拟合结果算成预测。</p>
<p>模型生成时间UTC：{A['generated_at_utc']}。明天18:00纽约时间的固定时点价格已保存在forecast_grid_4_events.csv。每日销售记录可以由同一组冻结系数在各自时间与座位条件下计算预测。若只拿到部分时段，明确报告部分窗口；没有销售记录的座位没有价格结果，不填零。</p>
<h2>6. 接下来需要的输入</h2><p>销售数据本轮已经更新。下一步提供9月30日当前在售的候选票，包含平台、采集时刻、Section、Row、必须购买的数量、每张或整组总价、费用与座位说明。有Listing ID或链接一并保留。拿到可买报价后，才能建立费用后价差、库存限制和退出情景。</p>
<h2>文件与可复查内容</h2><p>当前全量清理数据：Harry_current_sales_20260929.csv。新四文件清理结果：new_files_cleaned.csv。新旧差异：reconciliation.csv、likely_field_revisions.csv、prior_rows_absent_latest.csv。预测与系数：forecast_grid_4_events.csv、updated_coefficients.csv、frozen_forecast_model.json。所有原输入、脚本及上述文件在完整研究包中。</p><p><small>旧输入SHA-256：{A['previous_input_sha256']}。v1源代码SHA-256：{A['model_v1_source_sha256']}。每份新导出的字节哈希及原始行号见source_manifest.csv。原始七字段逐项验证保留。</small></p></main></html>'''
write(O/'Harry_MSG_update_20260929.html',body)
write(ROOT/'README.txt','''Harry MSG 2026-09-29 update

Run update.py and build_report.py with Python, pandas, NumPy and SciPy. OPENBLAS_NUM_THREADS=1 is recommended. Raw files are in raw/. The previous full cleaned snapshot and coefficients are in input/. model_v1_frozen.py is copied from the prior project. update.py extracts only the unmodified design/fit/baselines functions via AST, so importing it does not rerun prior backtests.

The latest snapshot replaces the three previously accepted overlapping events and adds October 2. It does not union both exports. Original files are preserved and six likely quantity revisions plus two older-only rows are recorded. No unique transaction ID is available. Identity is supported by user-supplied filenames and historical fingerprints, not platform event IDs.

Forward evaluation window: Sep 30 00:00 to Oct 1 00:00 America/New_York, pre-show rows only. Use frozen_forecast_model.json coefficients without refitting to score future observations. The posted v1 coefficients are retained separately for retrospective checks. Quantity zero means unknown. Quote predictions are base per-ticket record prices, not executable quotes or net seller proceeds. All times, window rules and main limitations are in the Chinese HTML report.

Other 26 event files are older snapshots. Activity coverage is not guaranteed stable. Small comparable-cell counts must remain visible. Lack of records is not evidence of no inventory or no sales.
''')
source=ROOT/'model_v1_frozen.py'
if not source.exists():shutil.copyfile(ROOT.parent/'msg_price_model/model_v1.py',source)
assert hashlib.sha256(source.read_bytes()).hexdigest()==A['model_v1_source_sha256']
base=ROOT/'input/Harry_cleaned_sales_previous.csv'
if not base.exists():base=ROOT.parent/'msg_seat_study/data/Harry_cleaned_sales.csv'
prev=ROOT/'input/previous_coefficients.csv'
if not prev.exists():prev=ROOT.parent/'msg_price_model/outputs/final_coefficients.csv'
zip_path=O/'Harry_MSG_update_20260929_package.zip';temp=zip_path.with_suffix('.zip.pending')
with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as z:
    for p in [ROOT/'update.py',ROOT/'build_report.py',source,ROOT/'README.txt']+sorted(R.glob('*.csv'))+sorted(O.glob('*.csv'))+sorted(O.glob('*.json'))+[O/'Harry_MSG_update_20260929.html']:
        z.write(p,p.relative_to(ROOT))
    z.write(base,'input/Harry_cleaned_sales_previous.csv');z.write(prev,'input/previous_coefficients.csv')
os.replace(temp,zip_path)
with zipfile.ZipFile(zip_path) as z:
    assert z.testzip() is None
    assert len(pd.read_csv(z.open('outputs/Harry_current_sales_20260929.csv'),low_memory=False))==38570
    for f in pd.read_csv(O/'source_manifest.csv').itertuples():assert hashlib.sha256(z.read('raw/'+f.preserved_file)).hexdigest()==f.sha256
print(json.dumps({'report_bytes':(O/'Harry_MSG_update_20260929.html').stat().st_size,'current_csv_bytes':(O/'Harry_current_sales_20260929.csv').stat().st_size,'package_bytes':zip_path.stat().st_size,'current_rows_verified':38570,'preserved_raw_files':4},indent=2))

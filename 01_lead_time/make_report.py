"""Build a Chinese research note from computed CSV outputs. Run after analyze.py."""
import base64
import html
import json
from pathlib import Path
import pandas as pd

R=Path(__file__).resolve().parent
P=R/'processed'
j=json.loads((P/'results.json').read_text())
f=pd.read_csv(P/'sales_enriched_all_records.csv',low_memory=False)
idx=pd.read_csv(P/'adjusted_price_indices.csv')
order=['gt7d','4to7d','48to96h','24to48h','12to24h','within12h']
labels=['7–30天','4–7天','48–96小时','24–48小时','12–24小时','12小时以内']
main=idx[idx.model.eq('main_30d')].set_index('time_bin').loc[order]
cal=idx[idx.model.eq('calendar_week_control')].set_index('time_bin').loc[order]
raw=pd.read_csv(P/'100_level_bins_full_history.csv').set_index('time_bin').loc[order]
near=pd.read_csv(P/'100_level_bins_main_30d.csv').set_index('time_bin').loc[order]

def table_md(df):
    def c(x): return str(x).replace('|','/').replace('\n',' ')
    return '| '+' | '.join(map(c,df.columns))+' |\n| '+' | '.join(['---']*len(df.columns))+' |\n'+'\n'.join('| '+' | '.join(map(c,row))+' |' for row in df.itertuples(index=False,name=None))

sources=[
('S1','SeatData FAQ','https://docs.seatdata.io/docs/faq/','价格不含费用；Qty=0表示数量未知；记录存在监测延迟。'),
('S2','SeatData sales API','https://docs.seatdata.io/docs/api/reference/v1/getEventSales/','sh价格/数量可能由挂牌信息补足；vs记录覆盖是下界；不得理解为完整市场逐笔成交。'),
('S3','Ticketmaster pricing','https://help.ticketmaster.com/hc/en-us/articles/9663528775313-How-are-ticket-prices-and-fees-determined','主办方制定票面价，转售方制定转售价；前台展示通常包含必要费用。'),
('S4','MSG official 2026 residency schedule','https://www.msgentertainment.com/madison-square-garden-harry-styles-together-together-30-shows-between-august-26-october-31/','确认15个已结束场次日期。'),
('S5','MSG indexed schedule','https://www.msg.com/','检索记录显示8/26与8/28为20:00 ET；动态页面可能更新。'),
('S6','Ticketmaster August 29 event','https://www.ticketmaster.com/harry-styles-together-together-new-york-new-york-08-29-2026/event/3B006435046481AA','8/29为20:00当地时间。'),
('S7','Ticketmaster Jamie xx schedule','https://www.ticketmaster.com/jamie-xx-tickets/artist/1506392?awtrc=true','检索记录显示9/2、9/4、9/5、9/9为20:00当地时间。'),
('S8','MSG indexed dates and times','https://www.msg.com/events-tickets/harry-styles-jamie-xx-madison-square-garden-october-2026/3B00643506AE83A2','检索记录含9/11至9/26各场20:00 ET；开场时间定义为预定活动开始，不是歌手实际上台。'),
('S9','MSG seating map','https://www.msg.com/madison-square-garden/seating/msg-knicks','仅用于场馆大类参考；体育座位图不能替代本次演唱会座位图。'),
]
pd.DataFrame(sources,columns=['source_id','title','url','what_it_supports']).assign(retrieved_local_date='2026-09-27').to_csv(P/'sources.csv',index=False,encoding='utf-8-sig')
time_sources=[]
for event in sorted(f.event_date.unique()):
    mmdd=event[5:].replace('-','')
    sid='S5' if mmdd in ['0826','0828'] else 'S6' if mmdd=='0829' else 'S7' if mmdd in ['0902','0904','0905','0909'] else 'S8'
    time_sources.append({'event_date':event,'scheduled_start_local':event+'T20:00:00-04:00','timezone':'America/New_York',
                         'source_id':sid,'url':next(s[2] for s in sources if s[0]==sid),'evidence_type':'retrieved_primary_source_page_or_indexed_excerpt'})
pd.DataFrame(time_sources).to_csv(P/'event_time_sources.csv',index=False,encoding='utf-8-sig')

groups={
    '100 Level：下层普通看台':['100 Level'],
    '200 Level：上层看台及其吧凳':['200 Level','200 Level Barstools'],
    '400 Level：更高层看台':['400 Level'],
    '地面区域：站席/Pit/Floor':['General Admission','Pit','Floor'],
    '桥廊及其吧凳':['Chase Bridges','Chase Bridges Barstools'],
    '西侧阳台及其吧凳':['West Balcony','West Balcony Barstools'],
    '俱乐部/休息区及其吧凳':['Madison Club','Lounge','Lounge Barstools'],
    '包厢':['Suites'],
    '未分类':['']}
seats=[]
for name,zones in groups.items():
    mask=f.zone.fillna('').isin(zones)
    seats.append({'大类':name,'原始Zone标签':' / '.join(zones) or '空白','记录数':int(mask.sum())})
seats=pd.DataFrame(seats)
assert seats['记录数'].sum()==len(f)
seats.to_csv(P/'seat_major_categories.csv',index=False,encoding='utf-8-sig')

quality=pd.DataFrame([
('原始记录',len(f),'全部保留，15个选用文件'),
('完全相同的记录候选',int(f.duplicate_candidate.sum()),'8组、16行；若每组仅留一条则减少8行。没有交易ID，默认不删'),
('数量未知 Qty=0',int(f.qty_unknown.sum()),'派生qty_known置空，价格分析保留'),
('数量非法',int(f.qty_invalid.sum()),'检查负数、小数、不可解析数值'),
('数量大于8',int(f.qty_large_review.sum()),'人工复核标记，最大20；不等于错误'),
('分区缺失',int(f.Zone.isna().sum()),'保留原始记录，不能加入100 Level分析'),
('排号缺失',int(f.Row.isna().sum()),'100 Level中34条；其余区域缺排号可能正常'),
('100 Level待复核排号',int(f.row100_review.sum()),'含GA、文字、三位数、组合排号以及少量23/30'),
('100 Level非普通数字Section',int(f.section100_review.sum()),'52条含WC后缀，2条仅写100 Level；不视为已证实错误'),
('预定开场时或之后',int(f.at_or_after_start.sum()),'单独保留，不纳入开场前模型'),
('价格/时间不可用',int((f.price_invalid|f.time_invalid).sum()),'检查非正、非有限价格及不可解析时间'),
('价格超过10000美元',int(f.price_above_10000_review.sum()),'只标记，不除以100、不猜测小数点'),
('稳健极端价格标记',int(f.price_extreme_review.sum()),'按zone+source，对数价格超过5倍稳健尺度，供复核'),
('冬季时间口径待确认',int(f.winter_timezone_ambiguous.sum()),'CSV表头EDT可能固定UTC-4；另保留纽约民用时区解释，主30天分析不受影响'),
],columns=['检查项','条数','处理方式'])
quality.to_csv(P/'quality_summary_cn.csv',index=False,encoding='utf-8-sig')

comparison=pd.DataFrame({'剩余时间':labels,'主样本记录数':main.records.astype(int).to_numpy(),
    '主样本价格中位数USD':near.median_price_usd.map(lambda x:f'{x:.2f}').to_numpy(),
    '座位等控制后指数':main.adjusted_index.map(lambda x:f'{x:.1f}').to_numpy(),
    '再控制日历周后指数':cal.adjusted_index.map(lambda x:f'{x:.1f}').to_numpy(),
    '后者探索性95%区间':[('基准定义' if b=='gt7d' else f'{cal.loc[b,"index_lower_95"]:.1f}–{cal.loc[b,"index_upper_95"]:.1f}') for b in order]})
comparison.to_csv(P/'q1_summary_cn.csv',index=False,encoding='utf-8-sig')
full=pd.DataFrame({'剩余时间':['7天以上（全部历史）']+labels[1:],'记录数':raw.records.astype(int).to_numpy(),
    '原始价格中位数USD':raw.median_price_usd.map(lambda x:f'{x:.2f}').to_numpy()})
specs=idx.pivot(index='time_bin',columns='model',values='adjusted_index').loc[order]
sens=pd.DataFrame({'检验':['只用sh来源','只用已知数量','剔除完全相同候选的多余行','前8场','后7场','开场假设提前1小时','开场假设推迟1小时','全部历史作为7天以上基准','额外控制成交日历周'],
    '最后12小时指数':[f'{specs.loc["within12h",k]:.1f}' for k in ['sh_only','known_qty_only','dedup_sensitivity','early_8_events','late_7_events','start_shift_-1h','start_shift_+1h','all_history','calendar_week_control']]})

flow=[]
mask=pd.Series(True,index=f.index)
for label,condition in [
    ('全部原始记录',pd.Series(True,index=f.index)),
    ('100 Level',f.zone.eq('100 Level')),
    ('价格时间可用且在预定开场前',f.eligible_price_prestart),
    ('距离开场不超过30天',f.hours_to_event.le(720)),
    ('普通数字Section 101–120',~f.section100_review),
    ('排号为1–22的普通数字排',~f.row100_missing&~f.row100_review)]:
    before=int(mask.sum());mask &=condition
    flow.append({'步骤':label,'保留记录数':int(mask.sum()),'本步不纳入数':before-int(mask.sum())})
flow=pd.DataFrame(flow);flow.to_csv(P/'sample_flow.csv',index=False,encoding='utf-8-sig')

protocol='''# 问题二：近期下跌是否预示未来几天继续下跌？

状态：假说和验证方案已固定，尚未运行动量预测模型。当前15场已用于问题一的探索，不能再称为未看过的测试集。

## 研究对象与目标

- 同歌手、同MSG、普通100 Level，保留来源、Section与Row。先不扩展场馆和艺人。
- 主预测期：未来3天。未来1天作为辅助。7天仅在覆盖充分时作为后续扩展，不能根据表现选择最佳期限。
- 目标是未来可比座位价格变化，不是订单能否成交、利润或可借券卖空收益。
- 主假说H1：在控制距离演出时间、座位构成和同期市场变化后，过去3天的价格跌幅对未来3天仍有增量预测信息（连续收益回归中动量斜率>0）。
- H0：控制这些因素后无增量预测价值。竞争假说为反转（斜率<0）。必须报告不支持H1的结果。

## 数据和观测时点

每日纽约时间20:00形成一次研究快照，且完整预测窗口必须早于该场预定开场。以到时已知的数据建立座位调整模型，禁止使用问题一的全样本回归系数。
每次保留event_key、as_of时间、训练记录最大时间、标签成熟时间、模型版本、过去窗口记录数、来源构成。
先比较过去72小时与再往前72小时的可比价格水平；每个窗口至少5条可用记录、覆盖至少2个Section，否则记为缺失，不插值成信号。
未来72小时窗口也要满足同样覆盖条件，但其是否合格只能在标签成熟时判定，并报告无法评价的预测比例。
来源支持发生变化时需保持固定来源组合，或用sh单一来源重做。

## 价格定义和共享端点问题

原型可以用上述窗口内经过当时可用模型调整的中位价格估计过去和未来收益。注意：近期窗口价格同时出现在过去收益分子和未来收益分母，估计噪声可能机械地产生反转。
因此正式检验必须增加一个验证：将近期窗口记录按固定record_key哈希分成A/B两半，一半仅用于过去收益端点，另一半仅用于未来收益的起始端点；每半至少5条，不满足则不评价该样本。规则在结果出现前固定。
再做不共享价格窗口的滞后验证：过去两段72小时的涨跌，是否预测未来第二个72小时相对第一个72小时的变化。这一验证实际需要未来6天，单独标注，不冒充3天结果。

## 基线、建模和验证

1. 基线A：价格不变。基线B：仅用倒计时和座位/来源信息的时间衰减模型。
2. 候选模型只在基线B上加入一个过去3天收益项，先用简单线性模型。初始不加入大量参数或调参搜索。
3. 以真实日历时间滚动训练和预测；在决策时刻t，训练样本的预测标签必须已完整结束且观测可得。将跨越训练/测试边界的标签剔除。
4. 不允许随机拆分交易行。同系列不同演出的售票期重叠，单按演出日期切分仍会泄漏。
5. 报告相对基线B的样本外MAE/RMSE、方向命中率、样本覆盖率；按预测日期和场次检查相关性，不能把每条销售当成独立试验。
6. 最近下跌的条件概率必须与相同倒计时条件下的总体下跌概率比较。例如80%对80%并没有增量信息。
7. 当前结果只用于探索。收到未来场次CSV后先确认其观测截止时间，把2026-09-27之后尚未实现的价格留作前瞻验证；上传“未来演出”的历史记录本身不会自动生成未来标签。

## 交易解释边界

若后续证据支持继续下跌，可作为等待买入、降低最高买价或减少已有库存的研究依据。必须另接历史/当前可执行报价、费用和库存约束才能模拟交易；不假定票务可卖空。
数据中没有未成交挂牌和撤单全过程，不能从销售记录直接估计自己的成交概率。
'''
(R/'Q2_protocol.md').write_text(protocol,encoding='utf-8')

source_md='\n'.join(f'- [{sid} · {title}]({url})：{note}' for sid,title,url,note in sources)
report=f'''# Harry Styles × MSG：数据检查与100 Level价格研究

研究版本：v1；数据收到日期：2026-09-27（美国中部时间）。范围：2026-08-26至2026-09-26共15场已结束演出。

## 结论先读

已保留并整理23,424条原始记录，其中100 Level为9,573条。第一问得到一个有条件的历史结论：临近演出时，普通100 Level的可比价格倾向下降。但“临期效应”和“同期市场整体下跌”混在一起。最后12小时的座位调整指数为71.9；加入成交日历周控制后为87.8（7–30天基准=100）。不能把28.1%的跌幅全部归因于倒计时。

第二问已建立可执行的检验方案，未声称近期下跌能预测后续下跌。等待未来场次数据后，按日历时间滚动验证；当前15场已被用于探索。

## 1. 原始数据与采用版本

raw/包含选用的15份原始CSV，字节不变。raw/superseded/保留旧0911、0912、0916、0918四份文件，不进入分析。9/11、9/12、9/16、9/18分别采用09111、09121、09161、09181。event_manifest.csv保存日期映射、SHA256和记录数。

CSV没有演出ID、交易ID、座位号或真实成交确认时间。场次归属来自用户核对后的文件名；官方日期与之相符。时间参考为纽约当地预定20:00，不是入场19:00，也不是艺人实际上台时刻。逐场证据见event_time_sources.csv。

每行新增event_date、event_key、source_file、source_row_number、record_key、observed_at_utc、event_start_local、hours_to_event、days_to_event_exact、calendar_days_to_event、time_bin及质量标记。原七列原样保留。文件名是来源文件；source/sh/vs是市场来源，二者分开。

## 2. 剩余时间规则

精确小时数h=(预定开场时间−记录时间)/3600，精确天数=h/24，不四舍五入、不把不足一天改写成半天。

- 12小时以内：0<h≤12。
- 12–24小时：12<h≤24。
- 24–48小时：24<h≤48。
- 48–96小时：48<h≤96。
- 4–7天：96<h≤168。
- 7天以上：h>168。
- h≤0：预定开场时或之后，单列而非塞入最后12小时。

CSV标注EDT，主解释固定UTC−4。1–3月历史记录可能存在EDT表头与纽约冬令时不一致，因此保留替代解释与标记；这些记录均在7天以上，不改变本报告的六组归属或最近30天模型。原始时间精度仅到分钟。

## 3. 检查结果

{table_md(quality)}

16条完全相同候选并非16条已证实重复交易。8组候选没有交易ID，同分钟、同区同排也可能是两笔独立交易。主数据全部保留，另有每组只留第一条的敏感性分析；这些候选不在主100 Level模型内。

极端价格最大82,450美元，应回查平台原记录；不能擅自除以100。全部15条超过10,000美元的记录均列入复核。100 Level两条早期极端价格在最近30天主分析窗口外。

## 4. 座位有哪些大类

这是对导出标签的研究分组，不是新的官方票种定义；同组内部仍有座位与权益差异。共有15个非空原始Zone标签，归为以下8个大类，另有未分类。

{table_md(seats)}

100 Level是下层看台类别，Section是具体分区，Row是排号。WC后缀单独保留，不能剥掉后缀后当作普通座位。首次模型只用普通数字Section101–120与Row1–22，这是保守的可比样本规则，不代表其余排号一定无效。

## 5. 是否存在官方标准价格

查阅MSG、Ticketmaster及SeatData后，未找到适用于这些场次所有100 Level座位的统一官方标准价，也没有取得逐场、逐Section/Row、逐票种的官方票面价表。Ticketmaster说明票面价由主办方决定，转售价由卖家决定。因此official_face_value_usd保持空值，不能把当前Get-in、网络最低价或单张票价当作所有100 Level的标准价。[S3]

SeatData价格是费用前的基础票价；Ticketmaster前台价格通常包含必要费用，两者不能直接相除算溢价。[S1,S3]

本版使用经验基准：最近30天窗口内，7–30天组的模型价格指数=100。它不是官方票面价、保证成交价或最高可接受买价。这个基准期的原始中位数是404.74美元，但每个Section/Row的模型基准不同，不能统一设为404.74美元。

## 6. 第一问：临近演出时可比座位价格如何变化

先给出按用户区间统计的完整历史，价格是记录等权、未按张数加权。数量未知记录保留，避免丢掉有效价格信息。

{table_md(full)}

完整历史的7天以上包括开售早期，可能与临期市场相差数月。因此主研究统一限制在演出前30天，再将7–30天作为参考。完整历史结果仍保留在100_level_bins_full_history.csv。

主模型：log(price)=场次固定效应+Section固定效应+精确数字Row固定效应+来源固定效应+数量组固定效应+倒计时区间效应+误差。
扩展模型额外加入记录发生的日历周固定效应。价格指数=100×exp(该倒计时区间的系数)。参考组=100是定义，不是该组真实价格没有不确定性。

{table_md(flow)}

{table_md(comparison)}

同一日期不同场次的票，距离演出时间不同；不同交易日期的市场整体价格也不同。加入日历周控制后，前4–7天和48–96小时相对基准的差异接近零，而最后48小时较低。这一控制不能完全消除日历效应，因为同系列场次高度相关、日历时间与倒计时交织。

最后12小时：基本控制后约低28.1%；再控制日历周后约低12.2%。后者探索性95%区间为指数82.6–93.4。标准误按15个场次聚类，小样本且跨场相关，区间可能偏窄，不应当作严格因果证据。

原始中位数不等于可比座位指数；不能将相邻行的中位数直接视为同一张票的收益。没有Seat Number，也无法完全控制视野、VIP权益、连座及隐藏品质。

## 7. 稳健性与数据能支持到哪里

{table_md(sens)}

改变来源、去掉未知数量、改变开场边界一小时后，基本模型的最后12小时指数约在71–73之间；最大的解释变化来自日历周控制，而非这些清洗选择。
严格匹配同场次、同Section、同Row、同来源，要求参考组至少3条、目标组至少2条时，最后12小时只有2个可比较单元，覆盖2场。因此同座位直接匹配不足以独立验证整个市场规律，当前依靠带控制变量的合并模型，不能声称做了逐座位重复销售指数。

这些数据是平台观察到的销售记录，不是完整交易所逐笔数据。sh的部分价格和数量来自挂牌信息补足，vs覆盖也受观测机制影响。[S2] 无挂牌买价、卖方净收入或未成交库存，因此本次没有回测PnL、成交概率或库存消化率。

## 8. 第二问：先固定假说，再做前瞻验证

要验证的是：同样接近演出、同样座位品质、同样市场环境下，近期跌得更多的票，未来3天是否还跌得更多。仅发现票价随倒计时降低不能证明动量。

主假说为过去3天的调整后收益对未来3天有正向增量预测力；竞争解释包括机械时间衰减、座位构成变化、市场共同趋势和价格估计噪声。Q2_protocol.md规定了基线、严格时间切分、标签成熟、稀疏窗口、共享端点噪声检验和结果评价。

本次交付状态：数据准备和第一问完成；第二问方案完成，尚无预测结果。你提供未来场次数据后，先登记截至时间、只用当时可见信息构造信号，未来真实价格到来后验证。历史文件是今天导出的，没有历史可见时间戳，早期回测仍需要声明报告延迟假设。

## 9. 文件与复现

- raw/：选用原始文件；superseded/：旧版本归档。
- processed/sales_enriched_all_records.csv：所有记录与派生字段，未删除记录。
- processed/quality_by_event.csv、flagged_records.csv、duplicate_candidates.csv：逐场审计和复核明细。
- processed/event_manifest.csv、event_time_sources.csv、sources.csv：输入映射和外部证据。
- processed/100_level_*：完整历史、主窗口、逐场、逐来源、逐座位统计及事后基准。
- processed/adjusted_price_indices.csv：全部模型和敏感性结果。
- figures/price_index.png：可导出的比较图。
- Q2_protocol.md：第二问冻结的初始方案。
- analyze.py与make_report.py：可复现代码；requirements.txt列出依赖。

解压后在项目目录运行：python analyze.py，然后python make_report.py。raw/中的原始文件已随包提供。结果是事后分析，任何benchmark字段都不可直接用于历史交易模拟。

## 10. 外部资料

检索日期：2026-09-27（美国中部时间）。动态页面可能跳转至未来场次，时间证据同时参考当次检索展示的官方索引记录。没有使用第三方票价广告来设置基准。

{source_md}

综合判断：数据整理置信度0.99；这一小样本的描述性结论置信度0.90；因果解释和未来预测尚未确立。
'''
(R/'research_report_cn.md').write_text(report,encoding='utf-8')

# Small self-contained HTML renderer: readable tables, no external dependencies.
parts=[]; in_list=False; table_lines=[]
def flush_table():
    global table_lines
    if not table_lines:return
    cells=[[c.strip() for c in line.strip().strip('|').split('|')] for line in table_lines]
    rows=['<tr>'+''.join('<th>'+html.escape(x)+'</th>' for x in cells[0])+'</tr>']
    rows+=['<tr>'+''.join('<td>'+html.escape(x)+'</td>' for x in row)+'</tr>' for row in cells[2:]]
    parts.append('<div class="table"><table>'+''.join(rows)+'</table></div>');table_lines=[]
for line in report.splitlines():
    if line.startswith('|'):table_lines.append(line);continue
    flush_table()
    if not line.strip():continue
    if line.startswith('# '):parts.append('<h1>'+html.escape(line[2:])+'</h1>')
    elif line.startswith('## '):parts.append('<h2>'+html.escape(line[3:])+'</h2>')
    elif line.startswith('- '):parts.append('<p class="item">'+html.escape(line[2:])+'</p>')
    else:parts.append('<p>'+html.escape(line)+'</p>')
flush_table()
img=base64.b64encode((R/'figures'/'price_index.png').read_bytes()).decode()
body=''.join(parts)
body=body.replace('<h2>7. 稳健性与数据能支持到哪里</h2>','<img class="chart" alt="100 Level price indices" src="data:image/png;base64,'+img+'"><h2>7. 稳健性与数据能支持到哪里</h2>')
doc='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MSG票务研究 v1</title><style>
body{font:16px/1.8 system-ui,"Microsoft YaHei",sans-serif;color:#203047;background:#f3f6fa;margin:0}main{max-width:1080px;margin:32px auto;padding:40px;background:white;border-radius:14px}h1{font-size:30px;line-height:1.4;color:#15395b}h2{font-size:22px;margin-top:36px;border-bottom:2px solid #dbe6f0;padding-bottom:8px}p{margin:12px 0;overflow-wrap:anywhere}.item{margin:5px 0 5px 20px}.table{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px;line-height:1.6;margin:16px 0}th,td{padding:10px 12px;border-bottom:1px solid #dbe3eb;text-align:left}th{background:#eaf1f8}tr:nth-child(even){background:#f8fafc}.chart{display:block;width:100%;margin:30px 0}@media(max-width:600px){main{margin:0;padding:20px;border-radius:0}h1{font-size:25px}}@media print{body{background:white}main{margin:0;padding:0;max-width:100%}table{font-size:10px}h2{break-after:avoid}tr{break-inside:avoid}.chart{break-inside:avoid}}
</style><main>'''+body+'</main></html>'
(R/'research_report_cn.html').write_text(doc,encoding='utf-8')

descriptions={
 'event_date':'演出日期，由已确认文件映射得到。','event_key':'本项目生成的场次键，不是平台ID。',
 'source_file':'采用的原始CSV文件名。','source_row_number':'原始文件行号，表头为第1行。',
 'record_key':'文件名+原始行号，审计用键，不是交易ID。','hours_to_event':'精确剩余小时，可为负。',
 'days_to_event_exact':'精确剩余天数=小时/24。','calendar_days_to_event':'纽约表面日期之差，仅作辅助。',
 'time_bin':'右闭区间；0<h≤12、12<h≤24等；h≤0单列。','qty_known':'正整数数量；0代表未知，派生值留空。',
 'duplicate_candidate':'同场原始七列完全相同的候选组全体；不等于证实重复。',
 'duplicate_extra_candidate':'每组保留首行时的额外行，仅敏感性分析使用。',
 'eligible_100_main_30d':'普通100 Level、开场前30天内、可解析价格时间、Section101–120及Row1–22。',
 'section100_wc_label':'Section包含WC后缀，单独保留，不与普通数字Section合并。',
 'section100_review':'不在普通数字Section101–120支持集；可能是合法特殊座位，不直接判错。',
 'row100_review':'非空排号不在普通数字1–22支持集；只标记和排除主样本。',
 'official_face_value_usd':'未找到可验证逐座位官方票面价，全部留空。',
 'observed_at_edt':'按原表EDT表头解释为UTC-04:00；不代表真实交易精确时间。',
 'observed_at_eastern_alternative':'按America/New_York民用时区解释的替代时间。',
 'winter_timezone_ambiguous':'两种时区解释不一致，通常为冬季记录。',
 'price_extreme_review':'zone+source内对数价格偏离中位数超过5个MAD稳健尺度，非自动删除。',
 'qty_large_review':'Qty>8的人工复核阈值，不是官方限购上限。',
 'price_above_10000_review':'价格>10000USD，仅标记供回查。',
 'at_or_after_start':'记录时间到达或晚于预定20:00活动开始，可能是晚售或延迟观测。'}
schema=[]
for c in f.columns:
    schema.append({'field':c,'description':descriptions.get(c,'原始导出列，保留原值。' if c in ['Date/Time (EDT)','Source','Zone','Section','Row','Qty','Price'] else '派生或审计字段，定义见analyze.py。')})
pd.DataFrame(schema).to_csv(P/'data_dictionary.csv',index=False,encoding='utf-8-sig')
(R/'README.md').write_text('''# Ticket research v1

Start with research_report_cn.html. Raw CSV bytes are preserved in raw/.

## Reproduce

Python 3.10+ with dependencies in requirements.txt:

```bash
python analyze.py
python make_report.py
```

No internet or paid API is needed to rerun. Q1 is descriptive, not a trading backtest.
Q2_protocol.md describes the pending continuation test. Full-sample benchmark columns MUST NOT be reused as historical trading signals.
The default sample is 100 Level, standard numeric sections and rows, <=30 days before the scheduled 20:00 New York show time.
Post-start observations and special seat labels are retained in the master but excluded from the primary model.
Identical minute-level rows are flagged, not automatically deleted. Unknown Qty=0 becomes missing only in the derived known-quantity field.
The original source file selection is explicit; old 0911/0916 must not be merged back in.
Model intervals are exploratory and may understate cross-event dependence. All events are one related residency series.
''',encoding='utf-8')
(R/'requirements.txt').write_text('numpy\npandas\nscipy\nmatplotlib\n',encoding='utf-8')
print(comparison.to_string(index=False))
print('Report created; original records preserved; Q2 pending new data.')

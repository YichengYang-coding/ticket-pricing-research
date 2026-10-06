"""Generate standalone Chinese research report and audit/source dictionaries."""
from pathlib import Path
import base64,html,json,re,sys
import numpy as np
import pandas as pd
import scipy,matplotlib

R=Path(__file__).resolve().parent;P=R/'processed'

def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])

def inline(s):
    s=html.escape(s)
    s=re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)',r'<a href="\2" target="_blank" rel="noopener">\1</a>',s)
    s=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',s)
    s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
    return s

def render(md):
    lines=md.splitlines();out=[];i=0
    while i<len(lines):
        s=lines[i].strip()
        if not s:i+=1;continue
        if s=='CHART_PLACEHOLDER':
            b64=base64.b64encode((R/'figures/q2_results.png').read_bytes()).decode()
            out.append('<figure><img alt="条件回归系数与滚动预测误差" src="data:image/png;base64,'+b64+'"><figcaption>左图：正值才支持动量。右图：误差越低越好。</figcaption></figure>');i+=1;continue
        if s.startswith('```'):
            buf=[];i+=1
            while i<len(lines) and not lines[i].startswith('```'):buf.append(lines[i]);i+=1
            out.append('<pre>'+html.escape('\n'.join(buf))+'</pre>');i+=1;continue
        if s.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                cells=[x.strip() for x in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r'[-: ]+',x) for x in cells):rows.append(cells)
                i+=1
            out.append('<div class="table-wrap"><table><thead><tr>'+''.join('<th>'+inline(x)+'</th>' for x in rows[0])+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+inline(x)+'</td>' for x in row)+'</tr>' for row in rows[1:])+'</tbody></table></div>');continue
        if s.startswith('#'):
            level=len(s)-len(s.lstrip('#'));out.append(f'<h{level}>'+inline(s[level:].strip())+f'</h{level}>');i+=1;continue
        if s.startswith('- '):
            out.append('<ul>')
            while i<len(lines) and lines[i].strip().startswith('- '):out.append('<li>'+inline(lines[i].strip()[2:])+'</li>');i+=1
            out.append('</ul>');continue
        para=[s];i+=1
        while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','- ','```')):para.append(lines[i]);i+=1
        out.append('<p>'+inline(' '.join(para))+'</p>')
    return '\n'.join(out)

def main():
    a=json.loads((P/'audit_new_uploads.json').read_text());accepted=json.loads((P/'audit_research_accepted.json').read_text())
    c=pd.read_csv(P/'conditional_coefficients.csv');m=pd.read_csv(P/'oos_metrics.csv');coverage=pd.read_csv(P/'sample_coverage.csv')
    man=pd.read_csv(P/'event_manifest.csv',keep_default_na=False)
    mainm=m[(m.variant=='all_sources')&(m.kind=='main')&(m.gap_days==0)].set_index('model')
    delta=mainm.loc['momentum'];prob=pd.read_csv(P/'down_probabilities_all_sources_main_gap0.csv')
    coefrows=[]
    cn={'main':'普通共用端点','split':'拆分端点','nonoverlap':'不共享窗口（需未来6天）'}
    for v,k,label in [('all_sources','main','普通算法'),('same_sample_as_split','main','普通算法：限拆分检验同样本'),('all_sources','split','拆分同一近期窗口'),('all_sources','nonoverlap','完全不共享窗口'),('sh_only','split','仅sh：拆分端点')]:
        row=c[(c.variant==v)&(c.kind==k)].iloc[0]
        coefrows.append([label,int(row.n),f'{row.coefficient:.3f}',f'[{row.lower95:.3f}, {row.upper95:.3f}]'])
    modelnames={'zero':'价格不变','baseline':'倒计时＋场次＋过去共同市场','momentum':'基线＋本场过去3天收益'}
    oosrows=[[modelnames[k],f'{r.mae_log_pp:.2f}',f'{r.rmse_log_pp:.2f}','—' if k=='zero' else f'{r.directional_accuracy:.1%}'] for k,r in mainm.iterrows()]
    robustrows=[]
    for v,k,gap,label in [('all_sources','split',0,'拆分端点'),('all_sources','nonoverlap',0,'不共享窗口（未来6天）'),('all_sources','main',6,'训练额外隔开6天'),('sh_only','main',0,'仅sh'),('dedup','main',0,'候选重复行去重'),('under_10000','main',0,'固定排除价格>$10,000')]:
        z=m[(m.variant==v)&(m.kind==k)&(m.gap_days==gap)].set_index('model');r=z.loc['momentum']
        robustrows.append([label,int(r.n),f'{z.loc["baseline","mae_log_pp"]:.2f}',f'{r.mae_log_pp:.2f}',f'{r.delta_mae_log_pp:+.2f}'])
    newrows=[]
    for r in man[man.upload_batch.eq('new_20260928')].sort_values('event_date').itertuples(index=False):
        newrows.append([r.source_file,r.event_date,r.row_count,r._asdict().get('_12','') if False else int(pd.read_csv(R/'raw'/r.source_file).Zone.eq('100 Level').sum()),'纳入' if r.included_in_research else '隔离：文件内容冲突'])
    qualityrows=[['本次原始记录',a['raw_rows'],'包含两份隔离文件；原始值全部保留'],['100 Level记录',a['100_level_rows'],'未清洗前'],['Qty=0',a['qty_unknown'],'未知数量，不作零票或一票'],['缺失Zone',a['missing_Zone'],'不猜补座位大类'],['缺失Row',a['missing_Row'],'其中100 Level缺失29条'],['100 Level非普通Row',a['row100_review'],'保留原始标签，主模型不用'],['100 Level特殊Section',a['section100_review'],'14条WC标签，不等于错误'],['完全相同行候选',a['duplicate_candidate'],'3组6行、额外3行；无sale_id不能证明重复交易'],['文件级冲突',2,'9/30与10/2两文件逐字节相同，各1,203行'],['价格或时间无法解析',a['price_invalid']+a['time_invalid'],'均为0'],['价格>$10,000',a['price_above_10000_review'],'14条；本次最高$415,881，标记待核查'],['对数价格MAD极值标记',a['price_extreme_review'],'84条，启发式标记，不自动删除'],['Qty>8',a['qty_large_review'],'30条，审查阈值不是平台限购'],['冬季时区解释差异',a['winter_timezone_ambiguous'],'EDT表头与纽约冬令时不同；保留两种解析']]
    text=f'''# Harry Styles / MSG：第二个交易研究假说

数据整理、3天价格动量检验与观众疲劳研究线索 · 2026-09-28

## 结论先行

**目前没有可靠证据支持：控制倒计时、座位差异及共同市场变化后，过去3天跌得更多，未来3天会继续跌得更多。**

普通算法出现较强反转关系，但它共用了一个有测量噪声的近期价格水平。拆分该端点以后，系数明显接近0，区间跨过0；进一步避免共享窗口也没有可靠的动量证据。因此既不应宣布找到下跌动量，也不应把初始负系数包装成已验证的反转策略。

滚动预测中，增加过去3天收益后，MAE由{mainm.loc['baseline','mae_log_pp']:.2f}变为{mainm.loc['momentum','mae_log_pp']:.2f}个对数百分点，没有改善；“价格不变”的MAE仅{mainm.loc['zero','mae_log_pp']:.2f}，更好。现有复杂模型尚未通过简单基准检验。

这是一项有明确可证伪假说、数据审计、统计控制、基线对比与防泄漏检查的研究。结果不支持最初设想也是有效结果，但当前不能称为可盈利交易系统。

CHART_PLACEHOLDER

## 1. 本次整理了什么

新上传15份文件共14,726条记录。9/30与10/2两份文件内容完全一致，均为1,203行，已保留但隔离；两份不能算两场独立数据。此前已确认的9/30旧文件sales_data.csv有1,277行，与争议新文件没有完全相同的交易行，继续作为旧快照使用。这不证明新文件属于哪一场，仍须重导核实。

**当前分析范围：29场、37,021条接受的原始记录；100 Level 14,745条，其中普通座位且开场前的合格记录14,434条。** 另外保留2,406条隔离记录；全部31份输入合计39,427行。原Q1结果未改写。

{table(['来源文件','演出日期','原始行数','100 Level','状态'],newrows)}

文件只有七个原始字段，没有真实event_id、sale_id或listing_id。日期依赖用户文件映射；开始时间为MSG官方排期20:00纽约当地时间，不是歌手实际上台时间。30日/31日Harryween也按官方时间处理。[MSG场次时间来源](https://www.msg.com/events-tickets/harry-styles-jamie-xx-madison-square-garden-october-2026/3B00643506AE83A2)。

### 新上传文件的质量检查

{table(['检查','数量','处理'],qualityrows)}

上表口径为本次15份原始上传，包含隔离文件，因此不是主模型样本量。缺失和极值不是互斥分类，不可相加当作总问题行数。数量异常0条、未知来源0条、新文件开场后记录0条。

原始七列均逐值保留，并附加场次日期、来源文件、原始行号、哈希、时间戳、精确距开场小时/天数、异常标记及是否入模。没有把可疑金额自动除100，也没有根据结果选删样本。候选重复默认保留，另做去重敏感性。

**倒计时分箱保留原规则**：(0,12]小时、(12,24]、(24,48]、(48,96]、(96,168]、>168小时；正好12小时属于12小时以内。原始小时/天数不四舍五入。开场时刻及之后单列。Q2用连续倒计时，完整未来3天窗口需在开场前结束，所以不覆盖最后72小时的3天预测。

SeatData价格不含手续费，Qty=0是未知数量。sh部分价格/数量依赖挂牌补充；vs观察计数是下界。CSV不是全市场销量或全部实际入场统计。[FAQ](https://docs.seatdata.io/docs/faq/) · [销售接口说明](https://docs.seatdata.io/docs/api/reference/v1/getEventSales/)。仍没有经过核实的统一100 Level官方票面标准价，因此本研究不用虚构票面价作锚。

## 2. 假说和可比价格怎样定义

主假说H1：过去3天收益系数β>0；过去收益越负，未来收益也越负，才叫持续下跌。β<0是反转方向，不能算支持H1。

研究对象为普通100 Level、Section101–120、数字Row1–22。这是沿用的保守可比范围，不是在断言其他座位不存在。每个72小时窗口至少5条、覆盖至少2个Section；不够就没有信号，不插值。

每日纽约20:00，用当时之前60天的价格拟合座位调整模型：log价格 ~ Section + Row + 来源 + Qty组 + 场次 + 售出日期 + 倒计时的非线性函数。只扣除座位/来源/数量构成项，保留价格随时间的变化。该时点系数冻结用于随后标签；没有借用Q1全样本基准，也没有用未来价格重新校准过去的座位差异。

```text
A = (t−6天, t−3天] 的调整后log价格中位数
B = (t−3天, t]     的调整后log价格中位数
C = (t, t+3天]     的调整后log价格中位数

过去收益 x = B − A
未来收益 y = C − B
```

这些是3天窗口价格水平的变化，不是精确到t这一瞬间的可执行报价。相同Section/Row仍可能有视线、具体座号和票种差异未观察到；“已控制座位”只指已记录的这些变量。

### 如何控制共同市场

**关联检验**：y ~ βx + 倒计时非线性项 + 场次固定效应 + 预测日期固定效应。日期效应吸收跨场次的同日共同变化；它是事后控制，不能拿未来日历效应做实时预测。

**滚动预测**：基线用倒计时、场次及其他场次过去收益的中位数（排除本场、至少5个同行场次）；候选模型仅多加一个本场过去收益项。这个共同因子只代表Harry/MSG系列，不代表整个美国票务市场，也不能消除所有异质新闻反应。

## 3. 条件关联结果

{table(['检验','场次×预测日样本','过去收益系数β','探索性95%区间'],coefrows)}

普通算法的约−0.49不应直接解读为赚钱的反转规律。因为近期价格B若偶然偏高，会同时把x推高、把y压低；即使真实价格没有反转，也会出现负相关。

拆分检验按稳定记录内容哈希把B分成两半：一半只用于过去收益，另一半只用于未来收益基准，各半仍需5条、2个Section。在**同样501个样本**上，共用端点系数−0.430，拆分后为−0.136。这与共享测量误差影响结果相符，但不能证明全部差异都来自该误差。

完全不共享窗口的检验预测“未来第4至6天相对第1至3天”的变化，系数约+0.038、区间跨0。它需要未来6天，不能冒充原始3天预测的完全替代检验。

区间按场次和预测日历周处理相关性，取双向及两个单向方差中较保守者。主检验只有9个日历周簇，拆分检验仅6个，区间是探索性的；重叠窗口与估计价格误差仍会限制统计把握，不能把791个观测当作791次独立实验。

## 4. 真正按时间往前走的预测

原计划8月1日起评价，但满足最少120条成熟训练样本、15个训练日后，主模型实际从8月19日才开始。每个预测时刻只用已经结束的标签训练，测试行不随机拆分。没有成熟标签的场次使用训练样本平均场次效应，预测表明确标注；这也是跨场外推的限制。

**647个可评价预测，29场、37个预测日，8月19日至9月24日**。共生成701个过去信息合格的预测；54个无法评价，其中41个尚未完整走完未来窗口，13个未来成交记录不足。主信号在2,275个候选场次日中只有869个具备信号和共同因子，覆盖率38.2%；不能假设每天每场都能交易。

{table(['模型','MAE：对数百分点','RMSE：对数百分点','涨跌方向准确率'],oosrows)}

MAE是平均绝对预测误差，越低越好；{mainm.loc['momentum','mae_log_pp']:.2f}个对数百分点不是{mainm.loc['momentum','mae_log_pp']:.2f}%的盈利，也不是{mainm.loc['momentum','mae_log_pp']:.2f}美元。单笔误差要转为价格比例需用exp(误差)−1。

加信号的MAE差值为{delta.delta_mae_log_pp:+.3f}个对数百分点（候选减基线，负值才是改善）；7天日历块重抽样的探索性95%区间为[{delta.delta_mae_ci_lower:.3f}, {delta.delta_mae_ci_upper:.3f}]，跨0。没有可靠的增量改善。样本中未来下跌比例为{delta.actual_down_share:.1%}，而加入信号后的方向准确率为{delta.directional_accuracy:.1%}，连“一直猜下跌”的方向基准也没有超过。

### 规定的敏感性检查

{table(['检查','可评价预测数','基线MAE','加信号MAE','误差变化'],robustrows)}

拆分端点、避免共享窗口，以及训练多隔开6天时，加入过去收益并未带来稳定改善。去重与固定极值检查不能改变总体判断。不同检查的可评价样本和目标有差别，不能横向把最低误差挑出来当最佳策略。

条件概率也不是统一结论：在距演出3–7天的61个样本中，未来下跌的总体比例约78.7%，过去已跌样本中约86.7%；但在14–30天样本中相应约68.1%与63.6%。小样本、日历共同变化和窗口重叠下，这些描述不足以证明增量预测价值。

## 5. 能否拿来决定买卖

当前不应只因过去3天下跌，就机械推迟买入、抛售库存或扩大头寸。也不应因普通算法显示反转就反向加仓。模型需要先在新增、真正未见的数据上稳定胜过简单基线。

本研究没有可执行买卖价、买卖费用、连续挂牌库存、未成交/撤单过程与自己的成交概率，因此没有计算交易PnL、最高买价或仓位。历史成交价不是你当时一定能买到或卖出的价格。

若后续要进入决策阶段，应先把目标改为可执行净卖价/售出概率，并接入买入费用、卖出费用、临近开场未售出的损失和资金/库存上限。在那之前，这是一份信号研究与否定性验证结果。

## 6. 时间与研究可信度

新数据最大记录时间为9月28日17:43 EDT，日度研究截至9月27日20:00。旧9/30文件只能覆盖更早的完整时段。每份文件按最后记录之前最近一次20:00作为保守完整截止点，这是操作性假设，不是平台完整性认证。

CSV缺少“该条记录首次何时对用户可见”。平台说明采集间隔可能从5分钟到12小时不等，历史文件也可能被回填或修订。因此本次是按记录时间构造的历史滚动模拟，不能宣称在当时实际拥有完全相同的信息；未来真正的前瞻验证需要保存当日导出与发布时间。

这批已结束场次也已被Q1探索过，不能称为从未看过的独立保留集。本次实施细则在查看模型系数和误差前写定，但不是第三方注册的预注册试验。

已验证原文件哈希与七个原始字段、场次隔离、成熟标签训练与误差复算。另做未来扰动检查：把t之后的价格全部乘7，当时的信号和共同因子完全不变，未来标签按预期改变。这支持实现按记录时间隔离了未来价格，不能弥补缺少首次可见时间的问题。

**把握程度**：对文件冲突与清理统计把握高；对“这版模型尚未证明动量预测价值”把握中高；对“市场永远没有动量/存在可交易反转/观众疲劳导致销量下降”均没有足够依据。

## 7. 新闻与第三个假说

'''
    news=(R/'news_and_q3.md').read_text()
    text+='\n'.join(news.splitlines()[2:])
    text+='''

## 8. 文件使用

- 总清理表：sales_enriched_all_files.csv，原始列保留；先看included_in_research和identity_status。
- 新文件审计：quality_by_event_new_uploads.csv、identity_checks.csv、event_manifest.csv。
- 模型复核：panel_*.csv、conditional_coefficients.csv、oos_metrics.csv、predictions_*.csv。
- 方法与复现：两个protocol、README、clean_data.py、analyze_q2.py、finalize_analysis.py、verify.py。
- latest_research_signals_not_trade_orders.csv是事后重建的9/27快照，不是9/27已发布过的前瞻预测或下单指令。

需要用户补齐的唯一文件问题：重新导出9月30日和10月2日，并保留各自网页event_id；两份当前相同文件不能靠改名解决。
'''
    (R/'MSG_Q2_report.md').write_text(text.replace('CHART_PLACEHOLDER','![条件关联与滚动预测误差](figures/q2_results.png)'))
    css='''body{margin:0;background:#f4f6fa;color:#1d2939;font:16px/1.8 -apple-system,BlinkMacSystemFont,"Noto Sans CJK SC","Microsoft YaHei",sans-serif}main{max-width:1100px;margin:32px auto;background:white;padding:42px 48px;border-radius:12px}h1{font-size:32px;line-height:1.35;color:#123c63}h2{margin-top:38px;color:#123c63;border-bottom:1px solid #dde5ee;padding-bottom:10px}h3{color:#175c9e;margin-top:28px}a{color:#175c9e}strong{font-weight:700}table{border-collapse:collapse;width:100%;font-size:14px}td,th{border:1px solid #dce3ec;padding:10px;text-align:left;vertical-align:top}th{background:#eaf0f7}tbody tr:nth-child(even){background:#f8fafc}.table-wrap{overflow-x:auto;margin:20px 0}pre{white-space:pre-wrap;background:#f3f6fa;border-left:4px solid #175c9e;padding:16px;font-size:14px}code{background:#f0f3f8;padding:2px 4px}figure{margin:25px 0}img{max-width:100%;height:auto}figcaption{color:#667085;font-size:13px}li{margin:8px 0}@media(max-width:700px){main{margin:0;padding:24px 18px}h1{font-size:26px}}@media print{body{background:white}main{margin:0;padding:0;max-width:none}table{font-size:11px}h2,h3{break-after:avoid}tr{break-inside:avoid}}'''
    document='<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Harry Styles MSG — Q2价格信号研究</title><style>'+css+'</style></head><body><main>'+render(text)+'</main></body></html>'
    (R/'MSG_Q2_report.html').write_text(document)
    sources=[
        ['N1','Vogue','2026-08-28','2026-08-26','https://www.vogue.com/article/harry-styles-madison-square-garden-review','媒体现场评论；售罄描述','不等于逐场入场或二级市场需求统计'],
        ['N2','Pitchfork','2026-09-10','2026-09-10','https://pitchfork.com/story/harry-styles-reveals-2027-tour-dates/','新增巡演新闻','可能分流需求是研究推断，尚未验证'],
        ['N3','FaceValue','','','https://facevalueto.ca/harry-styles-together-together-tour-2027/','独立票务评论：疲劳及第二轮公告后价格走弱','精确首次发布时间未核实；不能作历史实时信号'],
        ['D1','SeatData sales API','','','https://docs.seatdata.io/docs/api/reference/v1/getEventSales/','来源差异及价格/数量口径','不等于完整市场销量'],
        ['D2','SeatData FAQ','','','https://docs.seatdata.io/docs/faq/','费用、数量未知、采集延迟','不是导出文件首次可见时间'],
        ['E1','MSG','','','https://www.msg.com/events-tickets/harry-styles-jamie-xx-madison-square-garden-october-2026/3B00643506AE83A2','未来场次20:00及Harryween','动态页面；活动排期非实际歌手上台时间']]
    src=pd.DataFrame(sources,columns=['source_id','publisher','published_date','event_date','url','evidence','limitation']);src['retrieved_date']='2026-09-28'
    src.to_csv(P/'news_and_method_sources.csv',index=False,encoding='utf-8-sig')
    dictionary=[['event_date','2026年场次日期，用户文件映射'],['source_file','原始导出文件名'],['source_row_number','原始CSV行号，表头计为第1行'],['record_key','来源文件+行号，不是真实sale_id'],['content_key','场次与七个原始字段SHA256'],['source_file_sha256','原文件字节哈希'],['included_in_research','False记录隔离保留，不入任何Q2模型'],['identity_status','日期身份检查状态'],['hours_to_event','预定开场时间减记录时间，精确小时'],['days_to_event_exact','精确小时除24'],['time_bin','右闭倒计时箱；<=0单列'],['qty_unknown','Qty=0，数量未知'],['price_extreme_review','全样本来源/座位类MAD审查标记；不用作预测删点'],['split_half','稳定内容哈希分成0/1两半'],['as_of','纽约20:00的历史决策时点'],['x','过去两个72小时调整log中位水平之差'],['y','未来72小时与近期72小时调整log中位水平之差'],['x_split','近期半样本B0减A'],['y_split','未来C减近期另一半B1'],['y_nonoverlap','未来D减C；需未来6天'],['market_x','排除本场后的其他合格场次x中位数，至少5场'],['label_end','标签结束时刻'],['seat_fit_max_time','座位调整训练记录的最大时间'],['training_max_label_end','滚动预测训练标签的最晚成熟时刻'],['event_in_training','False时场次效应为训练样本平均值'],['prediction_momentum','基线加过去收益的预测；系数不强制为正，不代表动量策略'],['scorable','未来标签成熟且达到覆盖要求'],['mae_log_pp','平均绝对log收益误差乘100，不是利润率']]
    pd.DataFrame(dictionary,columns=['field','meaning_cn']).to_csv(P/'q2_data_dictionary.csv',index=False,encoding='utf-8-sig')
    versions={'python':sys.version,'numpy':np.__version__,'pandas':pd.__version__,'scipy':scipy.__version__,'matplotlib':matplotlib.__version__}
    (R/'environment_versions.json').write_text(json.dumps(versions,indent=2));(R/'requirements.txt').write_text('\n'.join(k+'=='+versions[k] for k in ['numpy','pandas','scipy','matplotlib'])+'\n')
    print('Report generated:',len(document),'characters')

if __name__=='__main__':main()

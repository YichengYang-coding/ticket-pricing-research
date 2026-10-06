"""Build a self-contained Chinese report and a reproducible research bundle."""
from pathlib import Path
import base64,hashlib,html,json,shutil,zipfile
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent;P=R/'processed';F=R/'figures';D=R.parent/'ticket_research_harry_deliverables';D.mkdir(exist_ok=True)
s=json.loads((P/'summary.json').read_text());v=json.loads((P/'verification.json').read_text())
pm=pd.read_csv(P/'price_models.csv').set_index('model');cm=pd.read_csv(P/'activity_models.csv').set_index('model')
bp=pd.read_csv(R/'comparison/BSB_price_models.csv').set_index('model');bc=pd.read_csv(R/'comparison/BSB_activity_models.csv').set_index('model')
history=pd.read_csv(R/'social/hshq_follower_history.csv');evidence=pd.read_csv(R/'social/evidence.csv').fillna('');sources=pd.read_csv(R/'social/sources.csv').fillna('')
def pc(x):return f'{x:+.1f}%'
def ci(r):return f'{pc(r.ci_low_pct)} 至 {pc(r.ci_high_pct)}'
def table(df):return '<div class="scroll">'+df.to_html(index=False,escape=True,border=0)+'</div>'
def image(name,alt):return '<figure><img alt="'+html.escape(alt)+'" src="data:image/png;base64,'+base64.b64encode((F/name).read_bytes()).decode()+'"></figure>'
def cite(id):
 r=sources[sources.source_id.eq(id)].iloc[0]
 return '<a href="'+html.escape(r.url,quote=True)+'">['+id+' '+html.escape(r.publisher)+']</a>'
windows=[(21,28),(14,21),(7,14),(0,7)]
horizon=[]
for lo,hi in windows:
 pp=pm.loc[f'fixed15_window_{lo}_{hi}'];cc=cm.loc[f'fixed15_window_{lo}_{hi}']
 horizon.append({'距开场时间':f'{lo}–{hi}天','场次数':15,'价格差异/晚10场':pc(pp.pct_per_10),'价格95%区间':ci(pp),'记录笔数差异/晚10场':pc(cc.pct_per_10),'笔数95%区间':ci(cc)})
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':150})
fig,axs=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
for ax,df,title in zip(axs,[pm,cm],['Adjusted prices','Observed 100 Level records']):
 qq=df.loc[[f'fixed15_window_{a}_{b}' for a,b in windows]];xx=np.arange(4)
 ax.errorbar(xx,qq.pct_per_10,yerr=[qq.pct_per_10-qq.ci_low_pct,qq.ci_high_pct-qq.pct_per_10],fmt='o-',color='#246b83',capsize=4)
 ax.axhline(0,color='#999',lw=.8);ax.set_xticks(xx);ax.set_xticklabels(['21–28 days','14–21 days','7–14 days','0–7 days']);ax.set(title=title,ylabel='% per 10 later shows',xlabel='Fixed first 15 completed shows; exploratory 95% CI')
fig.savefig(F/'fixed15_horizons.png',bbox_inches='tight');plt.close(fig)
fig,ax=plt.subplots(figsize=(10,3.5),layout='constrained');dates=pd.to_datetime(history.metric_date);delta=history.followers-history.followers.iloc[0]
ax.plot(dates,delta/1000,'o-',color='#246b83',ms=4);ax.axvline(pd.Timestamp('2026-09-10'),ls='--',color='#C47722',label='Sep 10: new 2027 cities announced');ax.axhline(0,lw=.7,color='#bbb')
ax.set(title='HSHQ Instagram: third-party dated follower observations',ylabel='Change from Aug 31 (thousands)',xlabel='Global account; snapshots are irregular and not an MSG demand measure');ax.legend();fig.autofmt_xdate();fig.savefig(F/'hshq_followers.png',bbox_inches='tight');plt.close(fig)
comp=[]
for name,pp,cc in [('Harry / MSG（17场）',pm.loc['primary_7_14'],cm.loc['primary_7_14']),('BBoys / Sphere夏季（21场）',bp.loc['primary_7_14'],bc.loc['primary_7_14'])]:
 comp.append({'样本':name,'100 Level记录':int(pp.n_records),'价格/晚10场':pc(pp.pct_per_10),'价格95%区间':ci(pp),'笔数/晚10场':pc(cc.pct_per_10),'笔数95%区间':ci(cc)})
pd.DataFrame(comp).to_csv(P/'Harry_BSB_comparison.csv',index=False,encoding='utf-8-sig')
q=pd.read_csv(P/'quality_audit.csv');qa=q[q.scope.eq('accepted')].set_index('check')
audititems=[('数量未知（原Qty=0）','qty_unknown'),('缺失Zone','missing_Zone'),('缺失Row','missing_Row'),('完全相同行候选：涉及行数','duplicate_candidate'),('候选去重会移除的额外行','duplicate_extra_candidate'),('价格稳健异常标记','price_extreme_review'),('价格超过$10,000','price_above_10000_review'),('计划开场时或之后记录','at_or_after_start'),('100 Level非常规Section','section100_review'),('100 Level缺Row','row100_missing'),('100 Level Row待复核','row100_review'),('冬季EDT/纽约民用时钟歧义','winter_timezone_ambiguous')]
audit=pd.DataFrame([{'检查项目':label,'数量':int(qa.loc[key,'count'])} for label,key in audititems])
checks=[]
labels={'primary_7_14':'主检验：7–14天','exact_section_row':'精确Section×Row控制','completed_first15':'仅已结束前15场','exclude_opening':'去首场','exclude_observed_endpoints':'去已观察样本首尾（并非实际尾场）','dedup_candidates':'候选行去重','exclude_price_flags':'去价格异常标记','known_qty_only':'仅已知数量','front_rows_1_11':'前半区Row1–11','levels_200_400':'200/400 Level普通数字座位','post_sep10_control':'加入9/10新城市公告标记','onsale_batch_control':'加入首次公开售票批次','all_days_presence_proxy':'每天都有记录的覆盖代理','all_zones':'全座区记录','followup_fixed15_0_28':'追加：前15场0–28天合计','followup_fixed15_0_28_allzone':'追加：前15场0–28天全座区','followup_last7_allzone':'追加：0–7天全座区'}
def modeltable(df):
 rows=[]
 for key,r in df.iterrows():rows.append({'检验':labels.get(key,key),'场次数':int(r.n_events),'差异/晚10场':pc(r.pct_per_10),'95%区间':ci(r)})
 return table(pd.DataFrame(rows))
mirror=evidence[evidence.source_id.eq('S09')][['show_date','period','value']].rename(columns={'show_date':'描述中的演出日期','period':'返回的缓存版本','value':'无标签计数1 / 计数2'})
snapshot=evidence[evidence.source_id.eq('S11')][['platform','account','metric','value']].rename(columns={'platform':'平台','account':'账号','metric':'网页指标','value':'网页数字'})
timeline=[
('8/28','首场评论积极，报道使用售罄描述','支持开场关注度高；售罄不等于转售价上涨','S03'),
('9/1','开场周现场采访：热情与机票、住宿、票价负担并存','预算约束与重复观看热情可以同时存在','S04'),
('9/10','官方宣布2027年12城25场，9/16公开开售','未来其他城市可能成为纽约的替代选择，这是待验证机制','S05'),
('9/15','校园媒体现场评论积极；描述当日排队后在票房买到票','支持现场体验；也提醒我们有临时放票这种供给因素','S06'),
('9/25','纽约快闪店仍有长队并引发邻里投诉','支持粉丝活动持续；商店排队不等于未来演出票需求','S07')]
news=''.join('<tr><td>'+dt+'</td><td>'+text+'</td><td>'+note+' '+cite(sid)+'</td></tr>' for dt,text,note,sid in timeline)
sourcehtml=''.join('<li id="'+r.source_id+'"><b>'+r.source_id+'</b> '+html.escape(r.publication_or_metric_period)+' · <a href="'+html.escape(r.url,quote=True)+'">'+html.escape(r.publisher)+'</a> — '+html.escape(r.research_note)+'</li>' for r in sources.itertuples())
endgrowth=100*(history.followers.iloc[-1]/history.followers.iloc[0]-1);peakdrop=int(history.followers.iloc[-1]-history.followers.max())
report=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Harry Styles：票价、交易活跃度与观众疲劳</title>
<style>body{{margin:0;background:#f3f5f5;color:#1f303b;font:16px/1.8 system-ui,-apple-system,"Microsoft YaHei",sans-serif}}main{{max-width:1100px;margin:auto;padding:40px 34px 70px;background:white}}h1{{font-size:32px;line-height:1.35;margin-bottom:10px}}h2{{font-size:23px;margin-top:38px;border-top:1px solid #dbe3e7;padding-top:24px}}h3{{font-size:18px}}.meta,.note{{color:#596b75;font-size:14px}}.lead{{background:#eaf3f4;border-left:5px solid #246b83;padding:18px 22px}}.warn{{background:#fff5e7;border-left:4px solid #c47722;padding:14px 20px}}.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:15px;margin:24px 0}}.card{{background:#f2f6f7;padding:16px}}.number{{font-size:28px;font-weight:750;display:block;color:#246b83}}table{{border-collapse:collapse;width:100%;font-size:14px}}th{{background:#e8eff2;text-align:left}}td,th{{padding:10px 12px;border-bottom:1px solid #dce4e8;vertical-align:top}}.scroll{{overflow-x:auto;margin:18px 0}}img{{width:100%;height:auto}}figure{{margin:24px 0}}a{{color:#166980}}code{{background:#edf1f3;padding:1px 5px}}details{{margin:18px 0}}li{{margin:8px 0}}@media(max-width:700px){{main{{padding:24px 17px}}.cards{{grid-template-columns:1fr}}h1{{font-size:26px}}}}@media print{{main{{max-width:none;padding:12px}}details{{display:block}}table{{font-size:11px}}figure{{break-inside:avoid}}}}</style>
<main><div class="meta">研究日期：2026-09-29 UTC · 数据沿用9/27–9/28导出 · 回顾性研究，不是已验证的交易策略</div>
<h1>Harry Styles / MSG<br>后期折价、交易时点与观众疲劳</h1>
<p>沿用 Backstreet Boys 的清理、可比座位、售票窗口与估计方法；新增固定前15场的窗口比较。研究对象是2026年纽约这轮演出，截至数据截点只演完前15场。不是对10月底整轮结果的提前定论。</p>
<div class="lead"><b>目前最合适的判断：后期场次存在较清晰的折价关联；最后一周普通100 Level的观察交易笔数下降，但28天合计没有明确下降。现场口碑与社交关注仍在，尚不足以认定“越演越疲劳”，也不能判定“越演越火”。</b></div>
<div class="cards"><div class="card">7–14天：调整价格<span class="number">−18.1%</span>每晚10场 · 95%区间−26.4%至−8.9%</div><div class="card">7–14天：观察交易笔数<span class="number">−4.7%</span>区间跨零，方向不明确</div><div class="card">0–7天：观察交易笔数<span class="number">−17.8%</span>仅前15场 · 探索性信号</div></div>
<h2>1. 我们究竟比较什么？</h2>
<p>想象比较第1场和第11场：都在开演前7–14天、同一来源、相近Section和Row、相同买票数量组，且控制演出是周三还是周末。问题是较晚演出的座位是否卖得更便宜。<b>这不是“同一张票过了10天跌了多少”，也不是预测未来必跌18.1%。</b></p>
<p>价格模型把座位、数量、距开场时间和星期的差异尽量扣除，再看演出顺序；每场演出总权重相同，避免交易多的场次主导结果。主样本为 <b>sh来源、100 Level、Section101–120、数字Row1–22、7&lt;天数≤14</b>，共17场、1,294条记录。这套字段筛选不保证每张票无视线遮挡，也无法识别所有VIP权益。</p>
<p>与BBoys保持同样的数量分组：未知、1、2、3、4、5张及以上。Harry上一版将3–4张合并；本版改为分别控制，因此主估计由约−18.09%轻微变为−18.12%，不是新增数据造成。价格指数以前6场平均=100；<b>100不是官方票面价，更不是保证可以成交的公允价</b>。未核实到每个Section/Row/票种统一的官方标准价，未虚构基准。</p>
<p>交易活跃度统计的是导出表内的<b>记录笔数</b>。一行可以含多张票，Qty=0表示未知数量；因此不能把笔数叫作票数、上座率或全市场销量。</p>
<h2>2. 数据清理与完整性</h2>
<p>31份当前导出共39,427行；其中两份标成10/2与9/30的新文件内容完全相同，身份无法确认，隔离2,406行。沿用旧9/30导出；10/2仍然缺失。接受29场、37,021行；原始文件、被替代旧版本、隔离文件和原始七列均保留。以下审计数量针对接受样本，标记可能重叠。</p>
{table(audit)}
<p>价格≤0、无法解析时间、非法数量和未知来源均为0。候选重复没有成交ID可核实，主检验保留，另做去重敏感性；价格异常仅标记并另做敏感性，不直接删掉高价。主模型中无重复额外行、无价格异常标记，52行数量未知。</p>
<p>保留精确小时差：0&lt;小时≤12、12&lt;小时≤24、24&lt;小时≤48、48&lt;小时≤96、96&lt;小时≤168、&gt;168。没有把不足一天直接当成12小时。EDT按UTC−4解释；演出计划开始按纽约20:00。最后一个实际观察时间之前最近的20:00作为保守截点，不随今天日期自动延长。</p>
<p>主窗口覆盖至10/3第18场，但第17场10/2缺失；更晚场次的窗口不完整，不记成零交易。17场在七个24小时桶中均有sh全座区记录，最大相邻观察间隔约{ s['max_gap_range'][0]:.1f}–{s['max_gap_range'][1]:.1f}小时。<b>这只能说明记录持续出现，不能证明采集覆盖稳定或完整。</b></p>
<h2>3. 后期折价：结果较稳定，但机制没有被识别</h2>
{image('harry_main.png','Harry按场次的调整价格指数与观察记录笔数')}
<p>主估计为每晚10场，调整价格{pc(pm.loc['primary_7_14'].pct_per_10)}，95%区间{ci(pm.loc['primary_7_14'])}。例如仅用于解释量级，$500×0.819约为$409；不能据此给某张未来票直接定价。图中仍有上下波动，斜率不是每一场都单调下跌。</p>
<p>精确控制Section×Row后约{pc(pm.loc['exact_section_row'].pct_per_10)}；只看已结束15场约{pc(pm.loc['completed_first15'].pct_per_10)}；去首场约{pc(pm.loc['exclude_opening'].pct_per_10)}；200/400 Level普通数字座位约{pc(pm.loc['levels_200_400'].pct_per_10)}。这些检查支持折价不是只由最便宜座位混入或单一首场高价造成。</p>
<div class="warn">加入9/10新巡演城市公告标记后，估计变为{pc(pm.loc['post_sep10_control'].pct_per_10)}，区间{ci(pm.loc['post_sep10_control'])}，不再明确排除零。它提醒我们：演出顺序与日历时间纠缠，新增替代城市、预算、供给等可能影响结果；不能说模型已完全控制共同市场变化，更不能把剩余折价全部命名为疲劳。{cite('S05')}</div>
<p>官方最初把30场一起宣布，但公开开售分三批。增加该批次控制后，价格为{pc(pm.loc['onsale_batch_control'].pct_per_10)}（{ci(pm.loc['onsale_batch_control'])}），笔数为{pc(cm.loc['onsale_batch_control'].pct_per_10)}（{ci(cm.loc['onsale_batch_control'])}）。主样本仅覆盖1/30当天上午与下午的两批，不能估计2/4第三批效应。{cite('S01')}</p>
<h2>4. 关键新增发现：最后一周变弱，可能也有购买时间前移</h2>
<p>为了避免不同售票阶段混入不同场次，下面四行都固定为8/26–9/26的前15场。数字仍是<b>较晚10场</b>的差异，不是一个窗口向下一个窗口的变化。</p>
{table(pd.DataFrame(horizon))}
{image('fixed15_horizons.png','固定前15场的四个售票阶段估计及区间')}
<p>最后一周价格约−26.6%、普通100 Level笔数约−17.8%，是值得继续追踪的“临场变弱”信号。但提前21–28天的笔数约+76.0%；7–14天笔数接近持平。不能只挑最后一周来证明整体疲劳。</p>
<p>看到上述形状后，我追加了28天合计检验：普通100 Level笔数{pc(cm.loc['followup_fixed15_0_28'].pct_per_10)}，区间{ci(cm.loc['followup_fixed15_0_28'])}；全座区{pc(cm.loc['followup_fixed15_0_28_allzone'].pct_per_10)}，区间{ci(cm.loc['followup_fixed15_0_28_allzone'])}。最后一周全座区笔数也没有明确下降（{pc(cm.loc['followup_last7_allzone'].pct_per_10)}，{ci(cm.loc['followup_last7_allzone'])}）。<b>因此信号更集中于普通100 Level的临场窗口。</b></p>
<p>一种可检验解释是部分交易提前发生；另一种是后期100 Level临场需求偏弱、座位或供给结构改变。没有买家身份、完整库存和采集日志，无法区分。这项28天检验是看到结果后追加的探索检查，不冒充事先设定的验证。</p>
<h2>5. 与BBoys放在一起看</h2>
<p>下面统一为sh、普通100 Level、开演前7–14天、每晚10场。座位具体编号按场馆分别定义；不能把MSG与Sphere的“100 Level”当作完全相同的商品。</p>
{table(pd.DataFrame(comp))}
<p>Harry的折价关联更清晰，但7–14天笔数趋势不明确；BBoys夏季后段在这个窗口的观察笔数上升，价格则有中段低、末段回升的形状。最后一周，BBoys价格约{pc(bp.loc['window_0_7'].pct_per_10)}、笔数约{pc(bc.loc['window_0_7'].pct_per_10)}，两者区间均跨零；Harry则显示较弱的临场价量。<b>两轮数据不足以得出“驻演一定导致疲劳”的通则。</b></p>
<p>对照限制：BBoys为7/16–8/29完整夏季21场，非其2025年以来全部驻演；Harry只有前半段已结束，主窗口还包括两场未来演出。两者城市、月份、场馆、票务供给、宣传与观众不同。这里未检验两位艺人系数之差的统计显著性。</p>
<h2>6. 社交媒体：拿到了什么数字？</h2>
<h3>Instagram账号历史：有波动，不能解释成一路疲劳</h3>
<p>HSHQ的第三方粉丝数：8/31为6,633,811，9/9为6,626,449，9/10为6,647,635，9/17为6,673,146，9/26为6,666,617。起末按计数计算约+{endgrowth:.2f}%，峰值之后少{abs(peakdrop):,}，约−0.10%。网站标题的+0.47%与端点计算略不同，本文用明确端点。走势在新城市公告附近上升，但只有时间重合，不能断言公告造成增长，也不能把之后小幅回落归因于MSG疲劳。{cite('S08')}</p>
{image('hshq_followers.png','HSHQ全球Instagram粉丝历史快照')}
<p>同一第三方页面还标出平均268,539赞、527评论；这是账号汇总，内容样本和帖龄口径不清，并非这15场每场的平均。HSHQ与Harry本人@harrystyles是不同账号，未混合比较。</p>
<h3>逐场帖子：保留数值，但不把未核验计数当真点赞</h3>
<p>下面数字来自公开镜像。日期来自描述中的演出日期，<b>不是已核验的发帖日</b>。A/B是本次检索返回的不同缓存，平台实际采集时间均未知；9/5同时出现两个版本。读取页面没有清楚标明逐帖两个计数是什么，也缺稳定原帖链接，所以不计算早晚场点赞跌幅或与票价相关系数。{cite('S09')}</p>
{table(mirror)}
<p>另一镜像出现286,865的无标签计数和明确标注的424条评论，但描述写9/5、图片标签写9/12、发布时间写9/13，已隔离日期关联。Instagram原帖无法读到，未升级为第一方确认。{cite('S10')} {cite('S15')}</p>
<p>镜像分析页还有自动生成的“互动下降”结论，混入专辑公告、巡演公告和普通演出照片，且帖子积累时间不同。本报告不采用它作为疲劳证据。{cite('S17')}</p>
<h3>TikTok、X、Facebook</h3>
{table(snapshot)}
<p>这些是Chartmetric页面标注9/28刷新时的约数；TikTok 77.3M是账号累计点赞，<b>不是MSG演出期间获得7,730万赞</b>。页面还有可疑的其他字段，所以以上只列为待核背景。未拿到可核验的逐场TikTok点赞/播放，也未获得固定口径的X与Facebook逐场互动历史，缺失不填零。{cite('S11')} {cite('S16')}</p>
<h2>7. 同期报道和社区反馈如何解释？</h2>
<div class="scroll"><table><tr><th>发表日期</th><th>实际看到的证据</th><th>解释边界</th></tr>{news}</table></div>
<p>社区并非全是一种声音。讨论8/29场的r/harrystyles帖子既有积极体验与重复观看意愿，也有时长相对票价不够划算的意见；这是开场早期便存在的评价差异，不能说后来才开始疲劳。{cite('S12')}</p>
<p>9/16“更容易买到票”的讨论主要涉及Rose Bowl等2027其他市场，评论也有人买票困难，不能移作MSG降温证据。r/Music的9/10新票价讨论在搜索索引中显示净得分2,001；这是可变化的净得分，不是2,001次购票，也不与其他帖子直接比较。{cite('S13')} {cite('S14')}</p>
<p>可继续使用的社区分工：r/harrystyles看演出体验与复购意向；r/Music看较广泛音乐讨论；本地媒体与现场乐评核查具体场次。它们都不是随机观众调查。“有投诉”或“新闻一直夸”本身都不能测量需求趋势。</p>
<h2>8. 研究判断、限制与下一步</h2>
<ul><li><b>后期折价：</b>样本内有较清晰关联，控制公告时间后不确定性增大。</li><li><b>整体交易萎缩：</b>28天合计和7–14天主窗口均未提供明确支持；不能把“没有显著下降”解读成证明没有下降。</li><li><b>临场变弱：</b>固定15场的普通100 Level有信号，需新增数据重复验证；多项探索检验未做多重比较校正。</li><li><b>观众疲劳：</b>仍是候选机制。票价受供给和时间约束影响；全球社交账号不是纽约边际购票者。</li><li><b>越来越火：</b>现场热情、新巡演讨论和较早成交可以并存，但没有同帖龄逐场社交数据支持持续升温趋势。</li></ul>
<p>优先更新同一批CSV至整轮结束，补正确10/2身份；保留抓取成功/失败日志与在售库存。逐场官方演出照片在发布后24/72小时固定观察点赞、评论、播放，记录发布时间和采集时间，分开普通演出、公告、名人热点。不要把今天看到的累计互动值放进历史时点的预测器。</p>
<p>监测工具可评估Chartmetric（音乐与跨平台指标）、HypeAuditor（Instagram历史）、先前BBoys研究中的Exolyt（TikTok）。购买前核实能否提供本账号、所需日期、逐帖ID与统一帖龄历史；本次未付费、未调用其API，不能承诺补齐历史。{cite('S11')} {cite('S18')}</p>
<p>交易研究上，可把场次顺序、售票阶段和公告事件作为待检验特征。但本报告尚未估计卖出概率、真实手续费、持有到期损失或可执行买价，因此不能由−18.1%直接产生买卖或仓位指令。</p>
<p><b>置信说明：</b>对“存在后期折价、但尚不能确认全面疲劳”这一谨慎结论，主观信心约0.85；这不是疲劳发生的概率，也不是模型输出。表中95%区间才是给定模型的统计不确定性，仍不覆盖所有漏变量和采集偏差。</p>
<details><summary><b>完整敏感性结果与统计方法</b></summary><h3>价格</h3>{modeltable(pm)}<h3>观察笔数</h3>{modeltable(cm)}
<p>价格：加权对数线性模型，场次顺序/10 + Section + Row + 数量组 + 距开场整数天桶 + 演出星期。每场总权重=1。价格误差允许同场次和同观察周相关，采用场次聚类、观察周聚类与双向聚类方差中最大者；t分布自由度取较少聚类数−1。精确座位检验替换成Section×Row类别。</p>
<p>笔数：Poisson均值模型，场次顺序/10 + 星期；同一检验中各场曝光天数相同。采用演出周聚类、HC1及过度离散调整方差中的最大者。只有5–7个时间聚类的小样本使推断不稳；这些区间是探索性的。方向统计为100×(exp(顺序系数)−1)。</p>
<p>代码与BBoys共享同一组估计函数。独立复核使用加权残差化方法重算主价格系数、按星期消去截距的轮廓似然重算主窗口/最后一周/28天笔数系数，并验证四个不重叠窗口恰好加成28天总数。</p></details>
<h2>来源与复现</h2><p class="note">检索日期为2026-09-29 UTC。网页检索日不等于平台计数采集日；全文未可读之处在来源表明确标注。没有复制新闻全文。</p><ol>{sourcehtml}</ol>
<p>完整包包括raw原始CSV、upstream旧清理逻辑和接受记录、processed新主表/质量审计/模型/场次表、social证据表/17个历史粉丝观察/未来采集模板、figures图表，以及prepare.py、analyze.py、model_functions.py、verify.py、build_report.py。原始七列逐字核对通过，39,427行主表中的included_in_research标记清楚区分隔离数据。</p></main></html>'''
(R/'Harry_BSB_method_report.html').write_text(report,encoding='utf-8')
shutil.copyfile(R/'Harry_BSB_method_report.html',D/'Harry_BSB_method_report.html')
shutil.copyfile(P/'sales_cleaned_all_records.csv',D/'Harry_cleaned_sales.csv')
shutil.copyfile(R/'social/evidence.csv',D/'Harry_social_evidence.csv')
checksums=[]
for p in sorted(R.rglob('*')):
 if p.is_file() and '__pycache__' not in str(p) and p.name!='checksums.csv':checksums.append({'path':str(p.relative_to(R)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
pd.DataFrame(checksums).to_csv(R/'checksums.csv',index=False)
with zipfile.ZipFile(D/'Harry_research_package.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(R.rglob('*')):
  if p.is_file() and '__pycache__' not in str(p):z.write(p,str(Path('Harry_research')/p.relative_to(R)))
print(json.dumps({'artifacts':[{'path':str(p),'bytes':p.stat().st_size} for p in D.iterdir()]},indent=2))

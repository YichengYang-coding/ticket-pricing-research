"""Build standalone Chinese report and an explicit, nonrepresentative evidence ledger."""
from pathlib import Path
from datetime import datetime,timezone
import json,html,base64,shutil,zipfile
import pandas as pd

R=Path(__file__).resolve().parent;P=R/'processed';S=R/'social';S.mkdir(exist_ok=True)
checked='2026-09-29 UTC'
sources=[]
def source(id,title,url,date,kind,status,notes):
 sources.append(dict(source_id=id,title=title,url=url,published_date=date,source_type=kind,access_status=status,checked_date=checked,notes=notes))
source('S01','官方夏季21场排期','https://backstreetboys.com/news/backstreet-boys-announce-their-final-three-summer-sphere-shows/','2026-03-16','artist_official','read','列出7/16–8/29全部21场；最后三场3/20公开售票。')
source('S02','7/16场次时间','https://www.bandsintown.com/e/107965805-backstreet-boys-at-sphere','2026-07-16','event_listing','read','明确20:00 PDT；其他场统一20:00为工作假设，非逐场实际登台时间。')
source('S03','SeatData FAQ','https://docs.seatdata.io/docs/faq/','','vendor_documentation','read','价格不含费用；Qty=0为未知；采集频率随事件活跃度变化。')
source('S04','SeatData Sales API','https://docs.seatdata.io/docs/api/reference/v1/getEventSales/','','vendor_documentation','read','sh部分价格数量来自listing补全；vs观测笔数为下界；CSV未带listing ID或监测覆盖元数据。')
source('S05','Sphere宣布跨年加场','https://www.sphereentertainmentco.com/backstreet-boys-to-ring-in-the-new-year-with-three-new-dates-for-the-into-the-millennium-sphere-residency/','2026-08-10','venue_press_release','read','新增12/31、1/1、1/2；称整个驻演累计47场售罄、超过75万人次。是主办方累计口径，非21场逐场热度。')
source('S06','官方再增加两场','https://backstreetboys.com/news/backstreet-boys-add-two-more-new-dates-for-the-into-the-millennium-sphere-residency/','2026-08-19','artist_official','read','新增12/26与12/27。增加供给和宣传冲击可能同时影响夏季场次。')
source('S07','People乐队访谈','https://people.com/backstreet-boys-share-secret-to-33-year-friendship-in-their-sphere-era-exclusive-12059657','2026-08-14','entertainment_press','search_excerpt_only','驻演给成员带来积极体验的访谈；不是观众统计，全文直接读取失败。')
source('S08','FSUniverse嵌入官方7/18 Instagram帖','https://www.fsuniverse.net/forum/threads/alysa-liu-cheer-fan-thread.106483/page-17','2026-07-18','third_party_embedded_social','read','嵌入注明29K likes、236 comments；缓存时间未知，不能当首24小时指标。')
source('S09','8/10官方Instagram帖的镜像','https://imginn.com/p/Db3fqFgtPj7/','2026-08-10','third_party_mirror','read','页面59,121未标注类型的计数及Comments(1974)；首个数字疑似点赞，未获原帖核验。搜索曾返回较旧58,864/1,968。')
source('S10','8/11官方Instagram帖的镜像','https://imginn.com/p/Db6jQ8Qvxdy/','2026-08-11','third_party_mirror','read','页面12,586未标注类型的计数及Comments(480)；首个数字疑似点赞，未获原帖核验。')
source('S11','HypeAuditor BSB Instagram历史数据','https://hypeauditor.com/instagram/backstreetboys/','','third_party_analytics','read_multiple_cached_versions','较早缓存含8/11粉丝6,262,878及8/29粉丝6,301,689；更新缓存为9月窗口。均非Instagram第一方实时值。')
source('S12','Reddit：第50场庆祝帖','https://www.reddit.com/r/BackstreetBoys/comments/1vqc1gx/backstreet_celebrating_50_shows/','2026-08-16','fan_community','read_and_indexed_score','官方内容转贴，评论有再次观演意愿；搜索索引234净票，不是Instagram点赞。')
source('S13','Reddit：值不值得飞去看','https://www.reddit.com/r/BackstreetBoys/comments/1vczayq/question_for_those_whove_gone_to_the_sphere/','2026-08-01','fan_community','read_and_indexed_score','多数已读回复积极，也提到预算限制；索引31净票。粉丝论坛选择性强。')
source('S14','Ticketmaster 7月评论','https://www.ticketmaster.com/artist/781254?page=9&tt_scene=anchor_view','','ticket_platform_user_reviews','search_excerpt','7/27评论者自称第4次观看仍喜欢；7/26评论同时称赞演出、批评时长和迟开场。不是统计抽样。')
source('S15','Ticketmaster 8月评论','https://www.ticketmaster.com/backstreet-boys-tickets/artist/781254?2269481858_177745934320_backstreet+boys+las+vegas=&GCID=0&gclsrcshybbb=aw.ds&page=3&tt_scene=anchor_view','2026-08-19','ticket_platform_user_reviews','search_excerpt','评论者称7月观看后计划买1/1场，是重复消费意向例子，不代表总体。')
source('S16','Touring Data票房页','https://touringdata.org/2025/08/21/backstreet-boys-into-the-millennium/','2025-08-21','secondary_boxoffice_aggregator','read_current_page','2026夏季七个周末仍为TBA。不可把2025票房误用于本次2026样本。')
source('S17','Exolyt账户分析功能','https://exolyt.com/features/account-overview','','analytics_vendor','read','说明TikTok账户、视频、历史增长及CSV导出功能；本次未购买或获得BSB历史数据。')
source('S18','Exolyt历史追踪说明','https://exolyt.com/guides/how-to-view-tiktok-analytics','2020-02-12','analytics_vendor_older_guide','read','旧指南称历史记录从加入服务后才有；购买前必须确认BSB所需日期覆盖，不假设可追溯全部过去。')
source('S19','Social Blade账户统计示例','https://socialblade.com/instagram/user/instagram','','analytics_vendor','read_search','提供粉丝及发帖等账户统计，部分功能需登录；未获取BSB逐帖历史。')
source('S20','官方第二批夏季场公告','https://backstreetboys.com/news/backstreet-boys-announce-another-six-sphere-dates-in-july-and-august/','2026-02-24','artist_official','read','场次分批公布；新增7/30–8/8六场，不能假定所有21场同日开卖。')
source('S21','TikTok官方账号检索','https://www.tiktok.com/@backstreetboys','','social_platform','robots_blocked','未取得逐帖点赞/播放量；没有将缺失填为0。')
pd.DataFrame(sources).to_csv(S/'sources.csv',index=False,encoding='utf-8-sig')
byid={s['source_id']:s for s in sources}
def link(id):
 s=byid[id];return '<a href="'+html.escape(s['url'],quote=True)+'">'+id+' '+html.escape(s['title'])+'</a>'
evidence=[]
def e(id,date,platform,account,topic,metric,value,display,sourceid,original_url,status,limit):
 evidence.append(dict(evidence_id=id,published_or_metric_date=date,platform=platform,account=account,topic=topic,metric=metric,value=value,display_value=display,source_id=sourceid,source_url=byid[sourceid]['url'],original_post_url=original_url,retrieved_date=checked,metric_snapshot_timestamp='unknown',post_age_hours=None,access_status=status,eligible_for_price_correlation=False,limitation=limit))
e('E01','2026-07-18','Instagram via forum','backstreetboys','SHE Weekend奥运及残奥女运动员到场','likes_rounded',29000,'29K','S08','https://www.instagram.com/reel/Da8vyBey-qR/','third_party_explicit_likes_label','特殊嘉宾内容；非普通每场回顾；原帖读取被限流；不是固定发布年龄数据。')
e('E02','2026-07-18','Instagram via forum','backstreetboys','同E01','comments',236,'236','S08','https://www.instagram.com/reel/Da8vyBey-qR/','third_party_explicit_comments_label','与E01同一帖子，不能算独立热度样本。')
e('E03','2026-08-10','Instagram mirror','backstreetboys','跨年三场加场公告','unlabeled_counter',59121,'59,121（疑似点赞，待核）','S09','https://www.instagram.com/p/Db3fqFgtPj7/','counter_type_not_explicit_in_text','页面未注明该数字类型；禁止当作已核实点赞；旧索引58,864不是同期基线。')
e('E04','2026-08-10','Instagram mirror','backstreetboys','同E03','comments',1974,'1,974','S09','https://www.instagram.com/p/Db3fqFgtPj7/','third_party_explicit_comments_label','镜像累计快照；原帖未核验。')
e('E05','2026-08-11','Instagram mirror','backstreetboys','8/27粉丝俱乐部感谢活动','unlabeled_counter',12586,'12,586（疑似点赞，待核）','S10','https://www.instagram.com/p/Db6jQ8Qvxdy/','counter_type_not_explicit_in_text','面向会员的窄受众公告，不能与加场公告直接比热度。')
e('E06','2026-08-11','Instagram mirror','backstreetboys','同E05','comments',480,'480','S10','https://www.instagram.com/p/Db6jQ8Qvxdy/','third_party_explicit_comments_label','镜像较旧缓存，统计截止时间未知。')
e('E07','2026-08-11','Instagram via HypeAuditor','backstreetboys','历史账户粉丝量','followers',6262878,'6,262,878','S11','','third_party_historical_row','全球账户指标，不是Vegas购票人数。')
e('E08','2026-08-29','Instagram via HypeAuditor','backstreetboys','历史账户粉丝量','followers',6301689,'6,301,689','S11','','third_party_historical_row','只支持这两个历史时点的增长，不证明逐场变热。')
e('E09','2026-08-01','Reddit','r/BackstreetBoys','是否值得飞去看演出','indexed_net_votes',31,'31','S13','','search_index_snapshot','净票非点赞；非平台实时核验；不同帖子不能直接当作时间序列。')
e('E10','2026-08-16','Reddit','r/BackstreetBoys','庆祝整个驻演第50场','indexed_net_votes',234,'234','S12','','search_index_snapshot','转贴热度与官方Instagram互动是两回事；搜索选择偏差。')
e('E11','','TikTok','backstreetboys','逐场演出视频','likes',None,'未取得','S21','','unavailable','robots限制；缺失不是0。')
pd.DataFrame(evidence).to_csv(S/'evidence.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(columns=['platform','account','post_url','published_at_utc','captured_at_utc','age_hours','content_type','related_show','likes_24h','views_24h','comments_24h','followers_at_post','paid_promotion','local_purchase_intent','fatigue_statement','missing_reason']).to_csv(S/'future_capture_template.csv',index=False,encoding='utf-8-sig')

s=json.loads((P/'summary.json').read_text());audit=pd.read_csv(P/'quality_audit.csv').iloc[0]
pr=pd.read_csv(P/'price_models.csv');ct=pd.read_csv(P/'activity_models.csv');events=pd.read_csv(P/'BSB_event_summary.csv')
def table(head,rows):
 return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+str(x)+'</th>' for x in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(c)+'</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table></div>'
labels={'primary_7_14':'主检验：提前7–14天','exact_section_row':'同Section×Row组合','exclude_first_last':'去掉夏季首场及末场','dedup_candidates':'候选重复去重','exclude_price_flags':'排除价格异常标记','known_qty_only':'仅数量已知','rows_12_22':'100 Level仅Row12–22','levels_200_400':'改用200–400 Level','announcement_cohort_control':'加入分批公告组','post_aug10_control':'加入8/10后日历标记','window_0_7':'提前0–7天','window_14_21':'提前14–21天','window_21_28':'提前21–28天','start_shift_-1h':'开演时间提前1小时','start_shift_+1h':'开演时间延后1小时','all_zones':'全部区域笔数','all_days_presence_proxy':'全区每天有记录的场次'}
def modeltable(df):return table(['检验','记录数','每后10场变化','探索性95%区间'],[[labels[r.model],r.n_records,f'{r.pct_per_10:+.1f}%',f'{r.ci_low_pct:+.1f}% 至 {r.ci_high_pct:+.1f}%'] for r in df.itertuples()])
def fig(name,caption):return '<figure><img alt="'+caption+'" src="data:image/png;base64,'+base64.b64encode((R/'figures'/name).read_bytes()).decode()+'"><figcaption>'+caption+'</figcaption></figure>'
socialrows=[['7/18','官方Instagram：SHE Weekend嘉宾','约29,000点赞；236评论','论坛嵌入明确标注；非原帖实时核验',link('S08')],['8/10','官方Instagram：跨年加场','59,121未标注计数；1,974评论','首个数字疑似点赞，待核；镜像缓存',link('S09')],['8/11','官方Instagram：8/27会员活动','12,586未标注计数；480评论','首个数字疑似点赞，待核；镜像缓存',link('S10')],['8/11 → 8/29','Instagram账户粉丝','6,262,878 → 6,301,689','第三方历史快照；增长约0.62%',link('S11')],['8/1 / 8/16','Reddit：观演咨询 / 第50场转贴','搜索索引净票31 / 234','两个不同帖子，不是同口径热度趋势',link('S13')+'；'+link('S12')],['7–8月','TikTok逐帖点赞及播放','未取得','受访问限制；不记为零',link('S21')]]
eventtable=table(['演出日','夏季序号','主窗口记录数','全区记录数','原始中位价美元','调整价指数'],[[x.event_date,x.order,x.ordinary100_count,x.allzone_count,f'{x.raw_median_usd:.2f}',f'{x.adjusted_index:.1f}'] for x in events.itertuples()])
body=f'''
<h1>后街男孩 Sphere 夏季驻演：票价、交易活跃度与观众热度</h1>
<p class="meta">2026-09-29 UTC研究快照 · 2026年7/16–8/29，共21场 · 回顾性探索研究</p>
<div class="lead"><p><strong>目前更符合“中段折价、尾段回升，同时提前购票窗口中的观察交易增多”。没有得到“连续演出导致观众逐渐疲劳”的可靠证据，也不能据此宣布持续升温。</strong></p>
<p>新闻和粉丝讨论中仍有加场、再次观演的积极线索。但逐场、同样发布后时长的社交互动数据不足，无法检验“点赞变化与票价变化相关”这一更具体的假说。</p></div>
{table(['问题','主检验结果','通俗解释'],[['后期可比座位更便宜？','每后10场 −15.4%；95%区间 −38.5% 至 +16.5%','整体点估计向下，但不够稳定；图中尾段回升'],['后期观察交易更少？','每后10场 +96.7%；区间 +39.0% 至 +178.4%','提前7–14天的样本内记录增加，方向与“越来越少”相反'],['真实需求更热／观众疲劳？','尚不能判定','缺少库存、完整监测日志和可比社交时间序列']])}
<p>主检验固定sh来源、100 Level数字排座位、每场开演前同样的7天，即7＜距离开场天数≤14，共512条记录、21场。控制Section、Row、数量分组、距离开场日桶、演出星期；每场价格模型权重相同。“每后10场”比较不同场次，不是持有同一张票10天的收益。</p>
{fig('bsb_main.png','蓝线为座位等因素调整后的逐场价格，前6场平均=100；柱形为同一提前期窗口的观察记录。虚线是线性概括，不能解释全部弯曲变化。')}

<h2>数据如何清理</h2>
<p>21份CSV共22,154行，原始文件字节、七列原始文本全部保留。新增来源文件、原始行号、SHA256、场次日期、UTC与太平洋时间、精确剩余小时／天数、时间组及质量标记。场次身份按用户文件名和官方排期对应；CSV本身没有event_id。21份文件没有完全相同的文件。BB801与BB806有1行七字段完全重合，保留为跨场次待核信息，不因此删除整个场次。{link('S01')}。</p>
{table(['检查','数量','处理'],[['无法解析时间／无效价格／无效Qty','均为0','仍不代表所有价格在经济上可信'],['候选重复','12行，含6条额外候选','无sale_id，主分析保留；去重作对照'],['数量未知Qty=0','5,521','设为未知，不补1，不用其推算售出票数'],['缺失Row','1,493','1,491空白＋2个NA类文本；100 Level缺排不进主样本'],['缺失Zone','4','保留原值，不强行猜区域'],['价格&gt;$10,000','19','标记待核，不自动截尾'],['同区域来源对数价格的稳健异常标记','50','可能与上项重叠；不是已确认错误'],['计划开演时点及之后','190','保留原始，排除开演前研究'],['冬季EDT表头歧义','3,635','按表头固定UTC−4转换并标记；不影响6–8月主研究窗口']])}
<p>价格最大值为$50,016，不能在没有票种／原始成交证据时直接认作普通票市场价。主样本512条里没有超过$10,000的记录、没有额外重复候选，有18条数量未知及1条稳健价格异常；去掉价格异常不改变主结论。标记可重叠，不能将上表相加当成“删除数量”。</p>
<p>文件写明EDT，夏季转换为拉斯维加斯时间要减3小时。7/16场次目录明确20:00 PDT，本次对21场统一使用当地20:00计划开演时间；逐场实际登台时间未取得。提前／延后1小时的主价格结果分别约−15.3%／−15.2%，不改变判断。2月份当地尚非夏令时，原表头是否固定EDT有歧义，已单列。{link('S02')}。</p>
<p>时间不四舍五入。按(0,12]、(12,24]、(24,48]、(48,96]、(96,168]小时及&gt;168小时统计；正好12小时归12小时内，正好24小时归12–24小时。开演时及之后另列。合并“300 level”和“300 Level”的标准化类别，原Zone文本保持不变。</p>
<p>区域分为100、200、300、400 Level、General Admission及少量套房／未分类。这里的100 Level研究组为Section101–110、数字Row12–37，共5,809行，其中5,768行是有效开演前记录。它只是可按排号调整的操作定义，不能保证全部无视线遮挡、非VIP，也不能把Sphere的100 Level与MSG当相同产品。</p>
<p>sh占22,044条；vs仅110条，最早出现于8/28 UTC，混合会造成来源覆盖变化。因此主模型固定sh。平台说明其显示价不含费用，Qty=0表示数量未知，部分sh价格／数量会用listing信息补全。{link('S03')}；{link('S04')}。</p>

<h2>票价：中段低、尾段回升，简单线性下降不稳</h2>
<p>例如，模型调整后指数7/16为137.9，8/13为54.6，8/20为55.1，最后三场依次79.3、90.0、100.4。这是同一模型对座位构成等差异作调整后的描述；不是实际可交易报价，也没有证明某一天发生了结构转折。最初几场每场只有9–13条主样本记录，单场指数尤其应谨慎看待。</p>
<p>主线性估计−15.4%的区间跨过0，意思是样本既容许下降，也容许一定上涨，不能排除无稳定线性变化。把Section与Row进一步合在一起比较，得到−12.7%，区间同样跨0。去掉首尾、仅数量已知、排除异常或改200–400 Level，均没有给出稳定的主窗口线性上涨／下跌证据。</p>
{modeltable(pr)}
<p>更早14–21天、21–28天窗口分别约−21.7%和−23.3%，而最后0–7天约+7.2%，后者区间跨0。<strong>提前期不同，结果不同</strong>，不能把较早窗口折价推广成“直到开演都越来越便宜”。这些是相关的多项探索检查，没有多重检验校正。</p>
<p>加入“交易日期8/10以后”的标记，场次顺序估计变为−36.2%。这个变动说明日历事件与场次顺序纠缠很深，不能把它选作最有利结果宣布疲劳成立。8/10有跨年场公告，但标记也会吸收其他同期变化；不是公告的因果效应。单轮驻演中，观察日期＝演出日期−提前期，不能同时声称充分控制任意日历变化又独立识别线性场次顺序。</p>

<h2>交易记录：较晚场次在较早窗口更活跃，但不能等同全市场销量</h2>
<p>前6场在主窗口平均每场11.5条，最后6场37.0条。星期调整后的计数模型估计每后10场增加96.7%；全部区域也增加79.5%，说明不只发生在100 Level。这里计量的是平台观察到的记录数，不是售出票张数、成交额、唯一买家或真实到场人数。</p>
{modeltable(ct)}
<p>最后0–7天窗口只估计增加9.7%，区间−25.5%至+61.5%；不能称“所有售票阶段都更活跃”。加入场次分批公告组后区间很宽，也提醒我们21场仍然是小样本。更合理的待检验机制是：购买时间可能前移、低价可能促进交易，或卖家库存和监测强度发生变化。</p>
<p>21场主窗口的每个24小时桶都能找到全区sh记录，最大观察间隔约9.7–22.8小时。没有整个日桶空白，<strong>但这不是稳定监测证明</strong>。平台采集频率随活跃度变化，CSV缺少监测日志。要将“记录增长”升级为市场需求结论，需要库存、挂牌数量、完整导出确认和历史覆盖信息。{link('S03')}。</p>
{fig('bsb_sensitivity.png','不同口径下的探索性区间。公告分组的活跃度区间很宽，反映小样本和解释变量高度相关。')}

<h2>社交媒体：实际找到的数字与缺口</h2>
<p>下面均是本次9/29 UTC检索时可见的公开内容或缓存。<strong>检索日不是指标真正统计截止时间。</strong>没有把它们冒充各帖发布后24小时的数字，也没有把疑似点赞计数写成已核实的点赞。</p>
{table(['帖子／指标日期','内容','看到的数字','数据质量','来源'],socialrows)}
<p>8/11到8/29粉丝增加38,811，约0.62%。这是“粉丝账户仍在增长”的弱线索，不能证明当地购票需求、每帖参与率或每场热度都上升。HypeAuditor返回过不同截止日的滚动页面，因此保留了历史行的指标日期，未把不同缓存当作同一时点。</p>
<p>7/18是特别嘉宾内容，8/10是跨年加场公告，8/11是面向会员的活动，受众和内容不同。即使原帖最终确认后两项都是点赞，也不能用29K→59K→12K直接推断先热后冷。旧帖积累更久、视频推荐、付费推广、特别嘉宾都可影响数字。</p>
<p><strong>本次未拿到足够的普通演出回顾帖序列，也未取得TikTok逐帖点赞／播放量，因此没有计算社交指标与票价的相关系数。</strong>Instagram直接读取失败／限流，TikTok受访问限制。没有以搜索结果数量或看不到帖子代替热度。证据CSV内所有条目均明确标为不适合直接做价格相关性检验。</p>

<h2>报道和观众反馈：支持持续兴趣，但不足以定趋势</h2>
<p>8/10 Sphere官方宣布增加跨年三场，称自2025年7月起累计47场售罄、超过75万人次；8/19官方又增两场。它们说明主办方仍选择增加供给，但属于累计、宣传口径，不能说明每一场转售价更高或逐场需求单调增加。{link('S05')}；{link('S06')}。</p>
<p>8/14 People访谈描述成员在驻演中的积极体验。它是乐队状态和媒体曝光的材料，不是观众疲劳测量。{link('S07')}。</p>
<p>7/27 Ticketmaster评论有人表示第4次观看仍很喜欢；8/19也有人写到7月看过后想买跨年场。Reddit8/1讨论可见重复观看与预算限制，8/16第50场庆祝转贴中也有再次观看意愿。这些提供“重复消费仍存在”的例子。{link('S14')}；{link('S15')}；{link('S13')}；{link('S12')}。</p>
<p>同时也看到对时长和迟开场的批评。它们可以是体验不满，却不是“连演越多导致兴趣下降”的同义词。已读内容是搜索便利样本，粉丝社区尤其偏向愿意发言的观众，不能计算总体正面率，也不能由没有找到明确疲劳报道断言疲劳不存在。</p>
<p>8/10公告对较晚场次既可能制造关注，也可能提供以后再看的替代选择。8/11公布的8/27会员感谢活动也可能影响尾段场次。当前时间对齐只能提出这些机制；本次没有识别哪一种导致价格回升。更不能用9月底累计互动数冒充8月份交易时已知的信号。</p>
<p>Touring Data当前页面2026年夏季票房与票数仍为TBA。其已有2025票房不可混入此次2026研究。售罄表述与二级市场价格下跌可以同时存在，因为一张已卖给转售者的票仍会在二级市场改变报价。{link('S16')}。</p>

<h2>与Harry项目如何连接</h2>
{table(['同为提前7–14天','Harry / MSG前次报告','BSB / Sphere本次'],[['样本','17场、1,294条普通100记录','21场、512条数字排100记录'],['每后10场调整价','−18.1%，区间−26.4%至−8.9%','−15.4%，区间−38.5%至+16.5%'],['每后10场观察笔数','−4.7%，区间−33.8%至+37.3%','+96.7%，区间+39.0%至+178.4%'],['目前可说什么','较明确的主窗口价格折价关联','价格形状弯曲，提前窗口记录增加']])}
<p>两个艺人的结果不一致，足以反对“长驻演一定越来越冷”的机械规则，但不能证明BSB没有疲劳或Harry存在疲劳。城市、场馆、粉丝结构、库存、座位视野和样本覆盖均不同；一个结果显著另一个不显著，也不等于两个系数差异已经显著。这是外部机制对照，不是随机对照或干净的双重差分。</p>

<h2>下一步可以真正检验的热度信号</h2>
<p>固定官方账号和普通演出回顾这一内容类型，完整记录帖子URL、发布时间、对应场次、发布后24／48小时点赞、播放和评论、当时粉丝数，以及是否广告、加场公告或特别嘉宾。再从同一规则采样的观众评论中分开标注“想再看”“已买下一场”“太贵去不了”“内容重复不想再看”。缺失与真实零分别记录。</p>
<p>交易研究中使用决策时刻已经形成的热度指标，预测之后3天的价格变化或观察交易；加入提前期、Section×Row、库存及公告等变量，与“没有社交指标”的模型比较。按时间向前验证，未来3天标签没有成熟时不能用于训练；同帖24／48小时数据也必须到其真正可见时才可使用。最终还要检验含手续费、可执行报价、未售出损失的收益。当前样本回顾不是盈利回测。</p>
{table(['可用工具','适合做什么','购买／使用前先确认'],[[link('S11'),'Instagram粉丝历史、帖子分析','是否覆盖7–8月、能否导出同龄逐帖指标；本次只读到公开部分'],[link('S17'),'TikTok账号、视频及历史增长、CSV导出','具体账号开始追踪日及逐帖历史深度；旧指南有追踪开始后才有历史的限制，见'+link('S18')],[link('S19'),'账户粉丝／发帖量变化','不能默认提供每条帖子发布后24小时数据']])}

<h2>逐场主窗口结果</h2>
{eventtable}
<h2>复现、检验与可信度</h2>
<p>原始数据、清理表、标记明细、时间分组、逐场结果、全部模型、社交证据及代码均在研究包内。clean_data.py生成字段及审计，analyze.py拟合模型，verify.py独立检查原始七列和文件哈希，并用残差化和独立Poisson轮廓似然复核两个主系数。全部核对通过。</p>
<p>价格用对数加权最小二乘，每场总权重1，报告100×[exp(β)−1]。区间使用场次聚类、观察周聚类和双向聚类中主系数最大的方差，t自由度7。计数模型用Poisson对数均值，方差取演出周聚类、HC1及过度离散修正中最大值，t自由度6。这种取最大值做法是谨慎的探索性选择，不保证任意依赖结构下的覆盖率；只有7个演出周，区间本身也有局限。</p>
<p><strong>可信度判断：</strong>对原始数据保留和清理核对为高；对“指定窗口样本内记录增加”为中等，受覆盖日志与分批公告限制；对“社交热度持续上升／下降”为低；对“观众疲劳导致票价变化”证据不足。这里的可信度是研究质量判断，不是统计置信区间或因果概率。</p>
<details><summary>完整来源目录（含访问状态）</summary>{table(['编号与来源','日期','类型／状态','用途与限制'],[[link(x['source_id']),x['published_date'],html.escape(x['source_type']+' / '+x['access_status']),html.escape(x['notes'])] for x in sources])}</details>
'''
css='''body{margin:0;background:#f3f6f8;color:#20323d;font-family:system-ui,-apple-system,"Noto Sans CJK SC","Microsoft YaHei",sans-serif;line-height:1.85}main{max-width:1100px;margin:28px auto;padding:40px 44px;background:white;border-radius:12px}h1{font-size:29px;line-height:1.4;color:#185a70}h2{font-size:23px;color:#185a70;margin-top:40px;border-bottom:1px solid #d7e4e9;padding-bottom:8px}p{font-size:16px}.meta,figcaption{font-size:13px;color:#607080}.lead{background:#eef6f9;border-left:4px solid #246b83;padding:4px 20px}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px;margin:20px 0}th,td{border:1px solid #dce5e9;padding:10px 12px;text-align:left;vertical-align:top}th{background:#e8f2f6}tr:nth-child(even){background:#f8fafb}a{color:#087198;overflow-wrap:anywhere}figure{margin:25px 0}img{width:100%;height:auto}summary{cursor:pointer;font-weight:600}strong{color:#163d4c}@media(max-width:720px){main{padding:20px 16px;margin:0}h1{font-size:24px}td,th{min-width:90px}}@media print{body{background:#fff}main{padding:0;margin:0}h2{break-after:avoid}figure,tr{break-inside:avoid}}'''
doc='<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>后街男孩票价与热度研究</title><style>'+css+'</style></head><body><main>'+body+'</main></body></html>'
(R/'BSB_report.html').write_text(doc)
D=R.parent/'ticket_research_bsb_deliverables';D.mkdir(exist_ok=True)
shutil.copyfile(R/'BSB_report.html',D/'BSB_report.html')
shutil.copyfile(P/'sales_cleaned_all_records.csv',D/'BSB_cleaned_sales.csv')
shutil.copyfile(S/'evidence.csv',D/'BSB_social_evidence.csv')
with zipfile.ZipFile(D/'BSB_research_package.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
 for p in sorted(R.rglob('*')):
  if p.is_file() and '__pycache__' not in p.parts:z.write(p,'ticket_research_bsb/'+str(p.relative_to(R)))
print(json.dumps({'report_bytes':len(doc.encode()),'sources':len(sources),'social_evidence_rows':len(evidence),'deliverables':[{ 'name':p.name,'bytes':p.stat().st_size} for p in sorted(D.iterdir())]},ensure_ascii=False,indent=2))

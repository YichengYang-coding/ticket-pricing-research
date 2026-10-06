from pathlib import Path
import json, math, base64, html, zipfile, hashlib, os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Ellipse, Circle

ROOT=Path(__file__).resolve().parent; O=ROOT/'outputs'
s=pd.read_csv(O/'section_summary.csv'); r=pd.read_csv(O/'row_effects.csv'); b=pd.read_csv(O/'row_bands_by_section_group.csv');c=pd.read_csv(O/'section_row_observations.csv');audit=json.loads((O/'audit.json').read_text())
groups={'A':[107,117],'B':[106,108,116,118],'C':[105,109,115,119],'D':[101,102,103,104,110,111,112,113,114,120]}
colors={'A':'#6B3FA0','B':'#217C9E','C':'#53A89A','D':'#C9DCE3'}
names={'A':'中央两侧正中','B':'正中两旁','C':'靠近长边的转角','D':'两端及外侧转角'}
s['group']=s.section.map({x:g for g,ss in groups.items() for x in ss})
s.to_csv(O/'section_summary.csv',index=False)
def poly(section):
    theta=math.radians((section-102)*18)
    aa=np.linspace(theta-math.radians(8),theta+math.radians(8),15)
    pts=[(5.0*math.cos(a),3.3*math.sin(a)) for a in aa]+[(3.8*math.cos(a),2.25*math.sin(a)) for a in aa[::-1]]
    return np.array(pts),theta
fig,ax=plt.subplots(figsize=(14,9.6),dpi=180);fig.patch.set_facecolor('#F7F9FC');ax.set_facecolor('#F7F9FC')
for row in s.itertuples():
    pts,th=poly(row.section);g=row.group
    ax.add_patch(Polygon(pts,closed=True,fc=colors[g],ec='white',lw=2))
    x=4.4*math.cos(th);y=2.77*math.sin(th)
    ax.text(x,y,str(row.section),ha='center',va='center',fontsize=13,fontweight='bold',color='white' if g in ['A','B'] else '#143447')
    ax.text(5.43*math.cos(th),3.65*math.sin(th),f'{row.all_history_index:.0f}',ha='center',va='center',fontsize=10,color='#445466')
ax.add_patch(Ellipse((0,0),6.2,3.25,fc='none',ec='#788998',lw=8,alpha=.28))
ax.add_patch(Circle((0,0),.64,fc='#243D51'));ax.text(0,0,'CENTER\nSTAGE',color='white',ha='center',va='center',fontsize=13,fontweight='bold')
ax.text(0,1.13,'OVAL CATWALK',ha='center',color='#586C7C',fontsize=10)
ax.text(0,-1.16,'Floor and production detail omitted',ha='center',color='#586C7C',fontsize=10)
ax.set_xlim(-6.1,6.1);ax.set_ylim(-5.15,4.3);ax.set_aspect('equal');ax.axis('off')
fig.suptitle('Harry Styles at MSG | 100 Level',fontsize=24,fontweight='bold',x=.5,y=.97,color='#18354A')
ax.set_title('20 sections, 4 exploratory price groups\nOuter numbers: adjusted price index (end sections = 100)',fontsize=12,color='#526779',pad=17)
for j,g in enumerate(groups):
    x=-5.5+(j%2)*5.8;y=-4.1-(j//2)*.63
    ax.add_patch(Polygon([(x,y-.14),(x+.22,y-.14),(x+.22,y+.1),(x,y+.1)],fc=colors[g]))
    vals=s[s.group.eq(g)].all_history_index
    sect_label=', '.join(map(str,groups[g])) if g!='D' else 'Ends + outer corners (10 sections)'
    label=f'{g}   '+sect_label+f'\n     Index {vals.min():.0f}-{vals.max():.0f}'
    ax.text(x+.35,y,label,fontsize=10.1,va='center',color='#233D50',linespacing=1.6)
fig.text(.06,.025,'Schematic only: not to scale, not a seat-level map. Colors show historical price groups, not guaranteed sightline quality.',fontsize=9,color='#617180')
fig.savefig(O/'MSG_100_Level_overview.png',bbox_inches='tight',facecolor=fig.get_facecolor());plt.close(fig)

fig,(ax1,ax2)=plt.subplots(1,2,figsize=(14,5),dpi=170,gridspec_kw={'width_ratios':[1,1.2]})
ax1.plot(r.row,r.all_history_index,marker='o',label='All history',color='#217C9E')
ax1.plot(r.row,r.within30days_index,marker='.',label='Within 30 days of show',color='#6B3FA0')
for x in [2.5,6.5,10.5,15.5]:ax1.axvline(x,color='#A9B8C4',ls=':',lw=1)
ax1.set(xlabel='Row label',ylabel='Adjusted index (Row 22 = 100)',title='Row premium declines gradually',xticks=[1,2,3,6,10,15,18,22]);ax1.legend(fontsize=8);ax1.grid(axis='y',alpha=.2)
mat=c.pivot(index='s',columns='r',values='n').reindex(index=range(101,121),columns=range(1,23)).fillna(0)
im=ax2.imshow(np.log1p(mat),aspect='auto',cmap='Blues',origin='upper');ax2.set_yticks(range(20),range(101,121),fontsize=8);ax2.set_xticks([0,1,2,5,9,14,17,21],[1,2,3,6,10,15,18,22]);ax2.set(xlabel='Row label',ylabel='Section',title='Observed records by Section and Row')
fig.colorbar(im,ax=ax2,label='log(1 + record count)',shrink=.8)
fig.tight_layout();fig.savefig(O/'MSG_row_diagnostics.png',bbox_inches='tight');plt.close(fig)

def table(df):return df.to_html(index=False,border=0,escape=True,classes='data',float_format=lambda v:f'{v:,.1f}')
def img(name):return 'data:image/png;base64,'+base64.b64encode((O/name).read_bytes()).decode()
tab=s[['section','group','all_sources_records','sh_model_records','observed_min_row','observed_max_row','observed_distinct_rows','unobserved_in_span','all_history_index','within30days_index']].rename(columns={'section':'Section','group':'建议分组','all_sources_records':'全部来源记录','sh_model_records':'分析记录 sh','observed_min_row':'最小观测排号','observed_max_row':'最大观测排号','observed_distinct_rows':'观测不同排号数','unobserved_in_span':'范围内未观察排号','all_history_index':'调整指数 全历史','within30days_index':'调整指数 开场前30天'})
tab=tab.fillna('—')
bandtable=b[b.row_band.ne('1-2')].pivot(index='section_group',columns='row_band',values='adjusted_index_rear100').reindex(index=['A','B','C','DE'],columns=['3-6','7-10','11-15','16-22']).reset_index().rename(columns={'section_group':'Section组','3-6':'前排 3–6','7-10':'中前 7–10','11-15':'中后 11–15','16-22':'后排 16–22'})
bandtable['Section组']=bandtable['Section组'].replace({'DE':'D'})
overview=[]
for g,ss in groups.items():
    v=s[s.group.eq(g)]
    overview.append({'组':g,'位置':names[g],'Section':', '.join(map(str,ss)),'调整指数范围':f'{v.all_history_index.min():.0f}–{v.all_history_index.max():.0f}','分析记录':int(v.sh_model_records.sum())})
sources=[
('MSG 官方演出页面','https://www.msg.com/events-tickets/harry-styles-jamie-xx-madison-square-garden-october-2026/3B00643506AE83A2','核实场馆与演出；官方通用地图注明布局随演出变化。'),
('MSG 官方座位图','https://www.msg.com/madison-square-garden/seating/msg-knicks','通用场馆参考，当前链接默认篮球配置；不能当作Harry完整演出图。'),
('Harry 演出舞台图及实拍','https://aviewfrommyseat.com/guides/harry_styles_together_together_tour/concert/New%2BYork/September%2B18%2B2026/','页面提供本轮中央舞台、椭圆走道图及现场视角；图非本报告自制分区图。'),
('SeatGeek 本轮演出座位指南','https://seatgeek.com/blog/best-seats-for-harry-styles-at-madison-square-garden-where-to-sit-for-the-together-together-tour','2026-08-31；中央圆台、椭圆走道、Kiss/Disco及Left/Right GA。'),
('Section 107 座位指南','https://www.rateyourseats.com/madison-square-garden/seating/sections/107','通常排号1–22；说明实际排号不等于本样本最小观测排号。'),
('Section 118 座位指南','https://www.rateyourseats.com/madison-square-garden/seating/sections/118','列出5–22；样本两条Row23保留为待核实。'),
('Section 101 座位指南','https://www.rateyourseats.com/madison-square-garden/seating/sections/101','通用指南列6–20，与本样本22排记录有出入，因此不据此强删或宣称本轮总排数。'),
('数据商采集方法','https://docs.seatdata.io/docs/sales-data-collection-methodology/','价格/数量可能推断，座位号未追踪，成交覆盖不完整。')]
pd.DataFrame(sources,columns=['title','url','use_and_limit']).to_csv(O/'sources.csv',index=False)
method='''对每条销售记录的美元单价取对数，使用场次、交易日历周、距离开场阶段、交易数量组、Section、Row的分类变量，采用Huber稳健回归。每场演出总权重相同；记录不按Qty加权，Qty=0作为未知组。距离开场保留原始小时，阶段为(0,12]、(12,24]、(24,48]、(48,96]、(96,168]小时，再细分7–14、14–28、28–56、56–112及112天以上。Section指数以101/102/103/111/112/113六个端部Section的几何平均效应归一为100。它是控制其他变量后的关联估计，不是官方票面价、未来售价或视线评分。'''
body=f'''<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Harry MSG 100 Level 座位分组</title>
<style>body{{font-family:system-ui,-apple-system,"Microsoft YaHei",sans-serif;color:#21384b;background:#f5f7fb;margin:0}}main{{max-width:1180px;margin:auto;background:white;padding:36px 46px}}h1{{font-size:32px}}h2{{font-size:23px;margin-top:36px}}p,li{{line-height:1.8}}.lead{{font-size:19px;background:#edf4f7;padding:20px;border-left:4px solid #217c9e}}.note{{background:#fff8e7;padding:16px}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{padding:10px 9px;border-bottom:1px solid #dce4ec;text-align:right}}th:first-child,td:first-child{{text-align:left}}th{{background:#edf2f6}}img{{width:100%;height:auto}}.scroll{{overflow-x:auto}}a{{color:#136886}}small{{color:#536678}}.cards{{display:flex;gap:16px;flex-wrap:wrap}}.card{{background:#eff4f8;padding:16px 25px;flex:1}}.card strong{{display:block;font-size:27px}}@media(max-width:700px){{main{{padding:20px}}table{{font-size:12px}}}}</style><main>
<h1>Harry Styles · MSG · 普通100 Level</h1><p>Section 与 Row 分组检查｜基于截至现有导出文件的历史记录｜分析日期：2026-09-29</p>
<p class="lead">建议第一版保留20个Section，并增加4个价格区域标签。普通排数采用3–6、7–10、11–15、16–22四档；1–2排单独处理。分组用于借用邻近样本，不应直接把组内所有票视为同价。</p>
<div class="cards"><div class="card"><strong>{audit['accepted_events']}</strong>有效场次</div><div class="card"><strong>{audit['candidate_100_rows']:,}</strong>100 Level候选记录</div><div class="card"><strong>{audit['model_rows']:,}</strong>固定sh来源的分析记录</div></div>
<h2>1. 舞台与Section概览</h2><p>Harry这轮MSG演出是中央舞台及椭圆走道。传统端头舞台的“正面／舞台背面”划分不适用。下面是自制拓扑示意图：标出Section相对环绕顺序，未按真实尺度绘制，也不包含具体座位、遮挡或通道。颜色来自本样本价格分析，不代表官方等级或观演保证。</p>
<img src="{img('MSG_100_Level_overview.png')}" alt="MSG普通100 Level的20个Section及四个价格分组示意图">
<div class="scroll">{table(pd.DataFrame(overview))}</div>
<p>A组靠长边正中、面对中央区域；B组在两旁；C组在长边转角；D组包括两端和外侧转角。票价有相对层级，但同一价格组不一定同一视角。D组一般更便宜，不等于不值得购买或视野差。117与107、116与106等仍保留各自Section，不强行设成同价。</p>
<h2>2. 每个Section出现了哪些排号</h2><p><strong>本表回答“数据中观察到了多少排”，不能证明“场馆总共只有多少排”。</strong>数据未包含完整座位清单。例如，公开指南给107通常1–22排，本样本却没有1–2排记录。101等通用指南与数据的21/22排标签有出入，118还有两条23排记录；均需对照具体场次售票图核实。</p>
<div class="scroll">{table(tab)}</div>
<p>候选记录中有70条带WC或未指定具体Section的记录，未混入普通席；普通101–120中有75条缺失/非纯数字Row，以及12条不在1–22范围的数字Row。以上原记录完整保留在核查文件中。第23排属于待核实，而不是已认定不存在。</p>
<h2>3. Row先分四个普通档，特殊前排另列</h2>
<table><tr><th>标签</th><th>排号规则</th><th>使用说明</th></tr><tr><td>特殊前排</td><td>1–2</td><td>单独参考同Section；1排仅10条分析记录，2排99条</td></tr><tr><td>前排</td><td>3–6</td><td>只包含该Section实际出现的排；如端部Section仅有6排</td></tr><tr><td>中前</td><td>7–10</td><td>主体样本覆盖全部20个Section</td></tr><tr><td>中后</td><td>11–15</td><td>主体样本覆盖全部20个Section</td></tr><tr><td>后排</td><td>16–22</td><td>105当前数据到20排；其余仍检查各排覆盖</td></tr></table>
<p>这四档是便于第一版使用的近似，不是已发现四条固定价格线。排数影响主要平滑下降；对四档分界做探索搜索，全历史偏向3/7/14，开场前30天偏向6/10/15，边界并不稳定。因此把1–2排单列，普通主体先采用6/10/15作为实用分界，后续保留精确Row继续检验。</p>
<img src="{img('MSG_row_diagnostics.png')}" alt="排数调整价格与Section Row样本覆盖图">
<p><strong>前排溢价也因区域而异。</strong>下表另用Section组×排档的交互模型，在控制场次、日历周、售票阶段、数量组和具体Section后，对每组的后排归一为100。它帮助判断不能把同一排数溢价套给所有区域。</p>
<div class="scroll">{table(bandtable)}</div>
<p>例如A组3–6排相对本组16–22排约高81%，D组则约高28%。这些是样本内模型估计，不是买卖报价。该表与上一张Section指数表来自不同诊断模型，不能直接相乘形成票价。</p>
<h2>4. 数据与方法</h2><p>输入为Harry_cleaned_sales.csv，共{audit['input_rows']:,}条，沿用前次身份核查：{audit['quarantined_rows']:,}条文件身份冲突记录保持隔离，接受{audit['accepted_rows']:,}条，覆盖29场。10月2日对应文件冲突仍未解决；本次没有补造该场数据。原文件未修改。</p><p>{method}</p>
<p>主分析保留1–22纯数字Row、合法开场前记录、正价格，固定sh来源，共{audit['model_rows']:,}条。9条既有价格异常标记和1条重复候选额外记录在主分析保留并稳健降权，另做排除敏感性检查；缺少listing ID不能断言候选重复一定是同一笔。数量未知共有{audit['model_qty_unknown']:,}条。</p>
<p>还检查了仅开场前30天、仅已结束场次、去除异常/重复候选、仅9月销售期、各区共同覆盖的6–20排。四个Section层级在这些诊断中保持基本顺序。所有分组均由已查看的历史数据提出，属于探索性分析；尚无独立未来数据验证，也未把相近系数宣称为统计等价。</p>
<h2>5. 后续计算可比中位数</h2><p>优先匹配：同场次＋同来源＋同Section＋同Row档＋过去72小时。样本不足时，展示更长窗口的独立参考，或在模型调整Section差异后借用同区域数据。不要直接合并A组和B组，也不要把缺少记录的排当成不存在。未来的新数据用来检查这套分组是否能提高估值精度。</p>
<p class="note">主要限制：没有精确Seat号码、视野遮挡标签和完整未售库存；Row范围不是官方座位清单；数据商观察记录可能有价格/数量推断；本次结论是价格关联，未证明视角造成差价，也不是未来盈利保证。</p>
<h2>来源与地图链接</h2><ul>{''.join(f'<li><a href="{u}">{html.escape(n)}</a>：{html.escape(note)}</li>' for n,u,note in sources)}</ul><p><small>数据输入SHA-256：{audit['source_sha256']}。完整代码、原输入快照、逐Section／Row统计、敏感性结果和审计文件见随附研究包。</small></p></main></html>'''
(O/'Harry_MSG_seat_groups.html').write_text(body,encoding='utf-8')
(ROOT/'README.md').write_text('''# Harry MSG 100 Level seat groups

Exploratory analysis of the user-provided cleaned sales snapshot. Run `analyze.py`, then `build_report.py` with Python, pandas, NumPy, SciPy and Matplotlib. Set OPENBLAS_NUM_THREADS=1 for predictable runtime.

The input remains byte-identical. `100_level_records_audited.csv` retains all candidate records; `model_records.csv` identifies analysis rows. `section_summary.csv` contains observed row coverage and six specification checks. `row_cut_candidates.csv` is descriptive cut exploration on fitted row effects with common full-sample row weights, not cross-validation or an official price taxonomy. All-history cut search enforces at least three consecutive row labels per ordinary segment; special rows 1–2 are separated by judgment after inspecting sample coverage. Exact row numbers are retained.

Diagram is a schematic with sections 102/107/112/117 at right/top/left/bottom. It is not to scale or a seat map. Floor detail omitted. Four groups summarize adjusted historical prices and do not prove equal quality or price within each group. Contemporary stage layout sources are linked in the report; generic maps can use other stage configurations.

No causal or out-of-sample performance claim is made. Source = sh. Prices are recorded per-ticket base prices, not all-in executable bids/asks. Record counts are unweighted by ticket quantity. Stage start follows the existing 20:00 New York convention, not inferred artist appearance time.
''',encoding='utf-8')
zpath=O/'Harry_MSG_seat_groups_package.zip';ztmp=zpath.with_suffix('.zip.pending')
with zipfile.ZipFile(ztmp,'w',zipfile.ZIP_DEFLATED) as z:
    for p in [ROOT/'analyze.py',ROOT/'build_report.py',ROOT/'README.md',ROOT/'data/Harry_cleaned_sales.csv']+sorted(O.glob('*.csv'))+sorted(O.glob('*.json'))+sorted(O.glob('*.png'))+[O/'Harry_MSG_seat_groups.html']:
        z.write(p,p.relative_to(ROOT))
os.replace(ztmp,zpath)
with zipfile.ZipFile(zpath) as z:
    assert z.testzip() is None
    assert len(pd.read_csv(z.open('outputs/model_records.csv'),low_memory=False))==audit['model_rows']
assert int(s.sh_model_records.sum())==audit['model_rows']
assert int(c.n.sum())==audit['model_rows']
assert int(b.n.sum())==audit['model_rows']
assert set(s.section)==set(range(101,121))
print(json.dumps({'groups':overview,'row_bands':bandtable.to_dict(orient='records'),'artifacts':{p.name:p.stat().st_size for p in [O/'MSG_100_Level_overview.png',O/'Harry_MSG_seat_groups.html',zpath]}},ensure_ascii=False,indent=2))

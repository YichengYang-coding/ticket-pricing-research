from pathlib import Path
import os,json,zipfile,html
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent;O=ROOT/'outputs'
audit=json.loads((O/'audit.json').read_text());m=pd.read_csv(O/'metrics.csv');p=pd.read_csv(O/'replay_predictions.csv');ex=pd.read_csv(O/'comparable_examples.csv')
def table(df):return df.to_html(index=False,border=0,classes='data',float_format=lambda x:f'{x:,.2f}',na_rep='不足5笔')
def atomic_text(path,text):
 t=path.with_suffix(path.suffix+'.pending');t.write_text(text,encoding='utf-8');os.replace(t,path)
by=[]
labels={'exact72':'同场同Section同排档，72小时','exact7':'同场同Section同排档，7天','section7':'同场同Section，7天（未匹配排档）','event7':'同场整个普通100 Level，7天'}
for rule,g in p.groupby('fallback_rule'):
 by.append({'回退层级':labels[rule],'记录数':len(g),'占比%':len(g)/len(p)*100,'模型平均美元误差':abs(g.model_price-g.price).mean(),'中位数基准平均美元误差':abs(g.fallback_median-g.price).mean()})
by=pd.DataFrame(by);by.to_csv(O/'baseline_coverage.csv',index=False)
tablem=m.copy();tablem['scope']=tablem.scope.map({'all_model_predictions':'全部预测','strict_72h_shared':'严格72小时共同样本','hierarchical_median_shared':'分层中位数共同样本'});tablem['method']=tablem.method.map({'model':'价格模型v1','strict_72h':'严格72小时中位数','hierarchical_median':'分层回退中位数'})
tablem=tablem[['scope','method','n','mae_usd','median_ape_pct','median_signed_pct']].rename(columns={'scope':'比较样本','method':'方法','n':'记录数','mae_usd':'平均绝对误差 USD','median_ape_pct':'绝对百分比误差中位数 %','median_signed_pct':'带方向百分比误差中位数 %'})
tex=ex[['s','r','model_price','strict_median','fallback_median','fallback_rule']].copy();tex.fallback_rule=tex.fallback_rule.map(labels);tex=tex.rename(columns={'s':'Section','r':'Row','model_price':'模型估计 USD','strict_median':'严格72小时中位数','fallback_median':'回退中位数 USD','fallback_rule':'回退口径'})
body=f'''<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Harry MSG 价格模型 v1</title><style>body{{font-family:system-ui,-apple-system,"Microsoft YaHei",sans-serif;background:#f4f7fa;color:#243c4e;margin:0}}main{{max-width:1100px;background:white;margin:auto;padding:36px}}h1{{font-size:31px}}h2{{margin-top:35px;font-size:22px}}p,li{{line-height:1.85}}.lead{{padding:18px;background:#edf5f8;border-left:4px solid #217c9e}}.note{{padding:15px;background:#fff7e2}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{padding:11px 8px;border-bottom:1px solid #dae4eb;text-align:right}}th:first-child,td:first-child{{text-align:left}}th{{background:#edf3f7}}.scroll{{overflow:auto}}a{{color:#17698a}}code{{background:#f1f4f7;padding:2px 4px}}small{{color:#617587}}@media(max-width:700px){{main{{padding:20px}}}}</style><main>
<h1>Harry Styles · MSG · 价格模型 v1</h1><p>普通100 Level，固定sh来源，Row 3–22｜2026-09-29</p>
<p class="lead">第一版已完成：根据座位、距离开场时间和过去市场记录，估计后续观察到的销售单价。27次逐日前推回放、4,955条销售记录中，平均绝对误差约$61.57；这衡量估值精度，不代表可成交收益。</p>
<h2>1. 上一张表不是所有成交价格的平均数</h2><p>上一份Section表是控制其他差异后的相对价格指数。Row表则把每个区域自己的后排设为100。因此D组前排128与A组中后排117不在同一基准上，不能直接比较。原始中位数、调整后指数、模型输出美元价格是三种不同的统计量。</p><p>Section是类别，不能用编号大小当作座位质量的连续刻度。Row可以尝试分段线性关系，但普通排数与很前面的排数采用不同斜率。v1直接使用具体Section和Row，并允许不同Section的排数影响不同。</p>
<h2>2. 模型在做什么</h2><p>模型形式：log(销售单价) = 场次差异 + Section差异 + Row影响 + Section与Row的联合作用 + 距离开场时间曲线 + 交易数量差异 + 近期共同市场趋势。</p><ul><li>取价格对数，让模型学习百分比差异，并避免产生负价格。</li><li>Row在第6排处允许斜率改变；不同Section可有不同的排数斜率。</li><li>距离开场使用已知小时数折算的精确天数，不把0.2天误改为0.5天。时间曲线使用log(1+天数)及固定节点。</li><li>最近90天作为训练范围，14天半衰期给近期记录更高权重。</li><li>稳健损失降低极端价格的影响；正则化限制稀疏座位的系数过度波动。</li><li>第1–2排共109条记录暂不纳入v1，保留为特殊前排问题。</li></ul>
<p>“线性”是指参数组合可用线性方法估计，不意味着原始美元价格随Row或Section编号严格走直线。本版未用前次全历史座位系数作为输入。</p>
<h2>3. 怎样按时间检查</h2><p>对2026年9月1日至27日，每天纽约时间零点只使用此前已知时间戳的记录拟合模型，预测接下来24小时实际观察到的销售记录。当天其他销售不会提前更新当天模型或基准。具体票的Section、Row、数量及已知开场时间用作条件。</p><p>有效研究全集13,345条，覆盖29场；本次回放包含26场的4,955条记录。每个预测场次需至少30条训练记录。没有销售的格子没有价格结果，不能填0。提供商的真实历史到达延迟及修订记录不可得，回放使用记录上的时间戳。</p><p class="note">这不是完全未见过数据的独立检验：此前研究已经看过这段历史。它是遵守先后顺序的历史回放。真正的未来检验需要冻结规则后，继续记录新预测并等待新数据。</p>
<h2>4. 模型与中位数比较</h2><div class="scroll">{table(tablem)}</div>
<p>平均绝对误差：例如预测$300、观察价格$250，计$50误差。绝对百分比误差中位数：一半样本的相对误差不超过这个数；11.80%不能解释为88.20%的成交成功率。带方向误差为正，表示倾向于高估。</p>
<p><strong>严格可比基准很稀疏：</strong>同场、同Section、同排档、过去72小时至少5条记录，仅覆盖48条待预测记录，占0.97%。这48条上模型平均误差$42.64，中位数$58.10，但模型只在其中50%的单条记录上更准，不能凭小样本宣称稳定胜出。</p>
<p>为了让所有预测有可比较基准，另设分层回退中位数。它会逐渐放宽排数条件，因此较弱，不能称为4,955条都有严格可比票。其构成如下：</p><div class="scroll">{table(by)}</div>
<p>模型平均误差比回退基准低约31.8%，且这次27个预测日均较低。这仍只是样本内项目开发后的历史回放结果；不能等同于交易盈利，也未给出独立统计显著性结论。</p>
<h2>5. 将两个座位放到同一美元口径</h2><p>以下统一为<strong>2026年9月30日演出、数量2张中的每张单价、sh来源、2026年9月28日纽约时间18:00</strong>的数据快照估计。不是今天实时挂牌价，也不含已经确认的买卖费用。</p><div class="scroll">{table(tex)}</div>
<p>这里Section 102第6排约$260，Section 107第15排约$324，不能支持“较便宜区域的前排总比较贵区域中后排贵”。对某些具体组合可能相反，必须在统一场次、时间及数量下比较。所有示例均缺乏满足5条门槛的严格72小时可比基准，应展示这一稀疏性。</p>
<h2>6. 目前完成什么，下一步做什么</h2><p>现在有一个能计算美元参考价格的估值模型。下一步冻结v1，记录新数据下的预测与误差，并将持有期明确为24或72小时。之后再加入真实买方总成本、卖方净回款、库存和退出期限，建立买入上限与仓位规则。现有销售数据没有完整未售列表，不能单独估计卖出概率，也不能把某笔历史价格当作自己保证能成交的价格。</p>
<h2>复查说明</h2><p>研究包包含协议、代码、每条回放预测、每日误差、最终系数、示例与审计。主输入仍为原Harry_cleaned_sales.csv；文件SHA-256：<code>{audit['input_sha256']}</code>。模型比较采用同一批记录，没有拿模型全样本与基准可覆盖子样本混比。</p><p>源文件身份冲突仍按前次规则隔离，10月2日没有补造数据。原始价格异常与重复候选在稳健主模型保留。Qty=0归为未知，不按售出票数加权。除独立回放核对外，没有为了改善结果进行参数搜索。</p></main></html>'''
atomic_text(O/'Harry_MSG_price_model_v1.html',body)
atomic_text(ROOT/'README.md','''# Harry MSG price model v1

Run model_v1.py, then build_report.py using Python with pandas, NumPy and SciPy. The default input path uses the byte-identical input/Harry_cleaned_sales.csv included in this archive, with a sibling-workspace fallback for the original development environment.

Read protocol.md for the fixed specification and evaluation conditions. This is retrospective conditional sale-price estimation, not a live quoting system or executed strategy backtest. Models are refit at each day boundary without access to later observations. Design choices were made after earlier research examined the full history, so future validation is still required.

Benchmark coverage must be reported: strict comparable 72-hour median covers 48 / 4955 predictions. The broader fallback benchmark uses weaker matches for most records. Mean absolute error and median percentage errors are prediction diagnostics, not profit or sell-through probability.

Model prices use source-record base USD values. Real fees, fill probabilities, timing delays, inventory, listing notes and individual seat numbers are not available. Section-row effects are regularized and front rows 1–2 excluded. Keep them separate.
''')
zip_path=O/'Harry_MSG_price_model_v1_package.zip';tmp=zip_path.with_suffix('.zip.pending')
with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
    for f in [ROOT/'model_v1.py',ROOT/'build_report.py',ROOT/'protocol.md',ROOT/'README.md']+sorted(O.glob('*.csv'))+sorted(O.glob('*.json'))+[O/'Harry_MSG_price_model_v1.html']:
        z.write(f,f.relative_to(ROOT))
    inp=ROOT/'input/Harry_cleaned_sales.csv'
    if not inp.exists():inp=ROOT.parent/'msg_seat_study/data/Harry_cleaned_sales.csv'
    z.write(inp,'input/Harry_cleaned_sales.csv')
os.replace(tmp,zip_path)
with zipfile.ZipFile(zip_path) as z:
    assert z.testzip() is None
    assert len(pd.read_csv(z.open('outputs/replay_predictions.csv')))==4955
    assert len(pd.read_csv(z.open('input/Harry_cleaned_sales.csv'),low_memory=False))==39427
print(json.dumps({'report_bytes':(O/'Harry_MSG_price_model_v1.html').stat().st_size,'zip_bytes':zip_path.stat().st_size,'verified_replay_rows':len(p),'model_mae':float(m[m.scope.eq('all_model_predictions')].mae_usd.iloc[0])},indent=2))

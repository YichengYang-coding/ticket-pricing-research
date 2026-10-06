# Harry Styles MSG 100 Level — Q2研究

任务：重复原数据清理，检验控制倒计时、座位与共同变化后，过去3天价格跌幅是否预测未来3天继续下跌；搜集驻演新闻并设计观众疲劳假说。

## 阅读顺序

1. `MSG_Q2_report.html` / `MSG_Q2_report.md`：结果、数据审计、方法、局限和新闻。
2. `Q2_original_protocol.md` 与 `Q2_implementation_protocol.md`：前期假说与本次实施细则。
3. `news_and_q3.md`：新闻来源与第三步设计。
4. `processed/conditional_coefficients.csv`、`processed/oos_metrics.csv` 与 `predictions_*.csv`：可复核数值。

`raw/`保存原始导出；`raw/quarantine/`明确标记两个内容相同但演出日期不同的新文件。所有原始列同时保留在`processed/sales_enriched_all_files.csv`，是否入模由`included_in_research`标记控制。

## 数据范围

15场已结束演出 + 13份身份不冲突的新文件 + 此前确认的9月30日旧快照 = 29场。当前没有可确认的10月2日数据。两个争议文件不会被当成两场独立观察。

文件不含event_id，日期来源是用户上传文件映射，开始时间按MSG官方20:00 ET。需要重新导出9/30与10/2、同时保存网页event_id后，才能解除隔离；不要只改文件名。

## 复现

依赖为Python3.12、numpy、pandas、scipy、matplotlib；报告生成仅使用标准库。版本见environment_versions.json。无网络调用、无API密钥、无付费请求。

在本目录执行：

```bash
python clean_data.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python analyze_q2.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python finalize_analysis.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python verify.py
python make_report.py
```

初次使用外部导出路径可加`python clean_data.py --input-dir /absolute/path/to/exports`。默认读取包内raw。所有输出在本目录和processed/，不覆盖输入CSV。

数值实现：OLS用SVD，截断相对奇异值1e-10以处理固定效应与未覆盖样条段的线性依赖；不根据预测效果调参。滚动模型场次效应按训练样本中心化，新场次无成熟标签时使用训练样本的平均场次效应，并在预测表标注event_in_training=False。

预测时间以记录时间为准，缺乏实际首次可见时间与当时快照，因此是历史滚动模拟，不是已完成的真实前瞻回测。最后3天未成熟标签不可用于验收预测。最新信号文件也明确标记为事后重建的历史快照。

此包未计算交易收益，也不含可执行报价、费用或实际库存。Q1报告未被改写。Q1清理逻辑留作参考文件，其原main()的固定样本断言不适用于本数据，实际入口是clean_data.py。

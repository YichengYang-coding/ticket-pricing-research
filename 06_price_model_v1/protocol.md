# Price model v1 protocol

Frozen before examining this version's evaluation results, 2026-09-29.

Question: Can a simple seat/time model estimate subsequent observed sales prices more accurately than recent comparable medians? This is conditional sale-price estimation, not executable quoting or fill-probability estimation.

Universe: the previously accepted Harry Styles MSG exports, Source sh, exact Sections 101–120, numeric Row 3–22, positive valid pre-start per-ticket recorded base price. Preserve all original data. Rows 1–2 remain a separate sparse-sample research problem. Prior duplicate candidates and price flags retained in the primary robust fit, not assumed false sales. Quantity zero remains unknown.

Daily replay: New York midnight on September 1–27, 2026. At each origin, fit on observations strictly earlier than the origin, from the preceding 90 calendar days. Predict observed sales in the next 24 hours. Their event, Section, Row, quantity group and known time to scheduled start describe each ticket. No information from another test-day sale updates that day's model or baselines. Timestamps are provider record timestamps; historical ingestion/revision latency is unavailable. This is a retrospective time replay, not a pristine untouched holdout: all history has already informed project design.

Strict benchmark: same event + Section + row band (3–6, 7–10, 11–15, 16–22), previous 72 hours, at least five records. Report coverage and compare on the same supported test rows. Operational fallback benchmark: strict, then same Section + band previous seven days with five records, then same event + Section previous seven days with five records, then same event ordinary 100 Level previous seven days with five records. The last two weaken comparability and are labeled. No cross-event raw-price pooling.

Model: robust ridge regression on log recorded price, Section category, event category, quantity category, piecewise Row (linear above Row 6 plus an extra slope before Row 6), Section-specific row slopes, linear spline in log(1+days_to_event) with knots at 1, 4, 7, 14 and 30 days, and a local calendar-time trend. Recent observations weighted with 14-day half-life. Fix penalties before results: intercept 1e-8, row/time continuous 1, Section and quantity 2, event 3, Section-specific row slopes 20. Huber delta 0.25 log-price units. No hyperparameter search. Normalize training weights to sum to training row count. Train once per origin.

Evaluation: MAE in USD, median absolute percentage error, median signed percentage error, and win fraction versus each benchmark on exactly matched rows. Also report each method's unweighted mean of per-event MAEs. Report all model-supported rows separately. No sale in an event-cell is a missing price outcome, not zero. Record coverage does not establish complete observation or actual trade availability. Daily paired error summaries are descriptive; no claim of independent observations or causal effects.

Snapshot examples: final origin 2026-09-28 18:00 America/New_York, predict candidate recorded sale prices at that instant. This is a historical snapshot; not live quotes. Demonstrate Section 102 Row 6 versus Section 107 Row 15 at September 30, quantity two, and related comparisons. Do not combine differently normalized indices. Do not issue inventory/buy/sell advice before separate execution assumptions and inventory inputs exist.

Deliverables: reproducible code, replay predictions/metrics, model coefficients, comparable-seat examples, Chinese explanation. Preserve original input hash and source identity. Historical forecast residuals describe observed price dispersion; no calibrated confidence/prediction intervals are promised in v1.

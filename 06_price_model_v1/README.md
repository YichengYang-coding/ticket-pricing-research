# Harry MSG price model v1

Run model_v1.py, then build_report.py using Python with pandas, NumPy and SciPy. The default input path uses the byte-identical input/Harry_cleaned_sales.csv included in this archive, with a sibling-workspace fallback for the original development environment.

Read protocol.md for the fixed specification and evaluation conditions. This is retrospective conditional sale-price estimation, not a live quoting system or executed strategy backtest. Models are refit at each day boundary without access to later observations. Design choices were made after earlier research examined the full history, so future validation is still required.

Benchmark coverage must be reported: strict comparable 72-hour median covers 48 / 4955 predictions. The broader fallback benchmark uses weaker matches for most records. Mean absolute error and median percentage errors are prediction diagnostics, not profit or sell-through probability.

Model prices use source-record base USD values. Real fees, fill probabilities, timing delays, inventory, listing notes and individual seat numbers are not available. Section-row effects are regularized and front rows 1–2 excluded. Keep them separate.

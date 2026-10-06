# Harry Styles / MSG — same-method comparison with BBoys

Analysis date: 2026-09-29 UTC. Existing September 27–28 exports, not newly acquired transactions. This is a retrospective research extension, not a backtested trading system.

Read `Harry_BSB_method_report.html` first. `protocol.md` separates predetermined harmonization from result-driven follow-ups. `processed/sales_cleaned_all_records.csv` includes the quarantined rows; filter `included_in_research == True` for the 37,021 accepted records. No transaction identifier is present, so duplicate flags are candidates only. Source sh/vs labels are retained as exported; source labels do not prove complete venue coverage.

Reproduce in this folder with Python, numpy, pandas, scipy, matplotlib:

```
python prepare.py
OPENBLAS_NUM_THREADS=1 python analyze.py
OPENBLAS_NUM_THREADS=1 python verify.py
python social/build_evidence.py
python build_report.py
```

The social evidence is a manual transcription of public facts and labeled limitations, not an automated historical scraper. The original raw exports and superseded files are preserved. `upstream` holds the earlier accepted data and cleaning implementation; `prepare.py` validates hashes and original columns before retaining earlier flags and recomputing lead time and harmonized derived features. Quantity 0 means unknown, not a zero-ticket sale. No official uniform face value was verified or imputed. Use `checksums.csv` to audit file bytes.

Price: equal event weights and clustered exploratory intervals. Activity: exported record counts, not units sold, attendance or total market demand. Future incomplete windows are excluded, never zero-filled. See `processed/window_eligibility_*.csv` for exact source reach and per-file cutoff. The 0–28-day aggregation and general-sale-batch control are explicitly exploratory additions.

`comparison/` contains only the completed BSB model/event-summary outputs needed to reproduce the comparison; the full BSB raw-data package was delivered separately. Different venues, seasons and observation cohorts are not a causal control group. Broad interpretation confidence is subjective, not a fitted probability of fatigue.

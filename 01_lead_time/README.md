# Ticket research v1

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

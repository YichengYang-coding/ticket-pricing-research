# Backstreet Boys / Sphere / 2026 summer

21 exports, 2026-07-16 to 2026-08-29. Research snapshot 2026-09-29 UTC.

Run with Python 3 plus pandas, numpy, scipy and matplotlib:

    python clean_data.py
    OPENBLAS_NUM_THREADS=1 python analyze.py
    python verify.py
    python build_report.py

Read BSB_report.html first. Original exports are preserved under raw/. The enriched table retains every original row and all seven original string fields. Generated prices/indices are retrospective adjustments, not out-of-sample forecasts. Social evidence is a manually verified, nonrepresentative discovery sample; missing metrics are not zero. No paid API calls or purchases were made.

processed/sales_cleaned_all_records.csv contains both eligible and flagged records. No automatic deletion or winsorization. Main model filters are explicit in protocol.md and analyze.py. A CSV row is one observed sale record, not a known number of tickets; Qty=0 means unknown.

Primary time assumption: fixed EDT (UTC-04:00) as stated in the CSV header; scheduled show start 20:00 America/Los_Angeles. Winter rows carry an ambiguity flag. Summer main windows are not affected by winter DST interpretation.

social/evidence.csv contains post/date/metric/type/provenance/limitations. Counts copied from cached third-party pages are not authoritative real-time Instagram metrics and are never treated as 24-hour values. TikTok individual post engagement could not be obtained.

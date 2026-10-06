# Harry MSG 100 Level seat groups

Exploratory analysis of the user-provided cleaned sales snapshot. Run `analyze.py`, then `build_report.py` with Python, pandas, NumPy, SciPy and Matplotlib. Set OPENBLAS_NUM_THREADS=1 for predictable runtime.

The input remains byte-identical. `100_level_records_audited.csv` retains all candidate records; `model_records.csv` identifies analysis rows. `section_summary.csv` contains observed row coverage and six specification checks. `row_cut_candidates.csv` is descriptive cut exploration on fitted row effects with common full-sample row weights, not cross-validation or an official price taxonomy. All-history cut search enforces at least three consecutive row labels per ordinary segment; special rows 1–2 are separated by judgment after inspecting sample coverage. Exact row numbers are retained.

Diagram is a schematic with sections 102/107/112/117 at right/top/left/bottom. It is not to scale or a seat map. Floor detail omitted. Four groups summarize adjusted historical prices and do not prove equal quality or price within each group. Contemporary stage layout sources are linked in the report; generic maps can use other stage configurations.

No causal or out-of-sample performance claim is made. Source = sh. Prices are recorded per-ticket base prices, not all-in executable bids/asks. Record counts are unweighted by ticket quantity. Stage start follows the existing 20:00 New York convention, not inferred artist appearance time.

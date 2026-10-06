# 10 — Oct 5 refit and prediction set v2

Refit of the 100 Level fair-value model on all data through Oct 5, 2026 06:19 UTC, with the same design, penalties, robust weighting and 14-day half-life as stage 06 and the Sep 29 frozen fit in stage 07. Fresh SeatData exports for the 15 shows from Sep 30 onward replace those shows' rows in the Sep 29 master (14,761 model-universe rows; 10,619 in the 90-day training window).

| File | Content |
| --- | --- |
| `refit.py` | The refit, the frozen-vs-refit comparison and the grids |
| `refit_oct5_model.json` | Coefficients and origin of the Oct 5 fit |
| `event_effects_frozen_vs_refit.csv` | Show effects vs the Aug 26 opener, Sep 29 fit vs Oct 5 fit |
| `oos_summary_frozen_v1_through_oct5.csv` | How the Sep 29 frozen model did on the 568 sales from Sep 30 to Oct 5, by show |
| `../outputs/forecast_and_buy_grid_refit_oct5.csv` | Prediction set v2: model price, max buy and break-even for four reference seats, T−7 and T−1 (committed separately as the pre-registration) |

Row-level exports are licensed and not included; `refit.py` documents the expected columns.

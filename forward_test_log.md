# Forward test log

Dated record of predictions made before the outcome and how they turned out. Entries are appended, never edited. All errors are on base prices, 100 Level, sections 101–120, rows 3–22, sales before showtime. "Ratio" is actual price ÷ model price; "error" is the median absolute percentage error.

## 2026-09-29 — Prediction set v1 frozen

Coefficients fixed at 22:36 UTC from all data to that time (38,570 rows, 30 shows). File: `outputs/frozen_forecast_model.json`. Pre-registered window: the Sep 30 show, from 00:00 ET on Sep 30 to showtime. Instruction recorded at the freeze: score with fixed coefficients and recorded timestamps; do not refit before scoring.

## 2026-10-01 — Window result and first week

| Scope | Sales | Ratio (median) | Error | MAE |
| --- | --- | --- | --- | --- |
| Pre-registered window, Sep 30 show | 35 | 1.05 | 7.8% | $36.6 |
| All sales since freeze, 5 shows | 232 | 1.03 | 11.0% | $40.9 |

Also recorded on Oct 1, before the fact: Oct 7 and Oct 9 trading 12–15% above model; recommendation was to sell inventory in those dates and not to buy.

## 2026-10-05 — Week two: the frozen model falls behind

Per-show summaries: `outputs/oos_summary_frozen_v1_through_oct5.csv`; by lot size and section group: `outputs/oos_summary_by_lot_size_oct5.csv`, `outputs/oos_summary_by_section_group_oct5.csv`.

| Show | Sales since freeze | Ratio | Error |
| --- | --- | --- | --- |
| Oct 2 (played) | 144 | 1.01 | 9.8% |
| Oct 3 (played) | 143 | 1.01 | 11.1% |
| Oct 7 | 80 | 1.25 | 25.2% |
| Oct 9 | 57 | 1.12 | 13.5% |
| Oct 10 | 67 | 1.13 | 18.2% |
| Oct 14 | 45 | 1.22 | 23.1% |
| Oct 16 | 32 | 1.09 | 16.2% |
| All | 568 | 1.07 | 13.5% |

Show-day windows (same construction as the Sep 30 window): Oct 2 — 43 sales, ratio 1.13, error 14.2%; Oct 3 — 49 sales, ratio 1.09, error 17.1%.

What happened: the model held for shows inside 48 hours and under-priced the later shows by 10–25%. The early-October Wednesday discount compressed from −25% to about −7% relative to the opener between Sep 30 and Oct 5, with volume on those dates rising (Oct 7: 8–16 sales a day in late September, 23 on Oct 4). Freezing the calendar-drift term does not explain it (ratios move by 0.02). No artist-specific catalyst found. Working hypothesis: demand spilling from the sold-down Oct 2–3 dates into later ones.

What it says about the method: a frozen fair value has a shelf life of about a week in a moving market. The Oct 1 "sell Oct 7 above 1.15 × model" call was right on expectation and wrong ex post — the show went to 1.37. Recorded as the cost of a mean-reversion rule in a trending week; the three-day momentum result (no predictability) stands, since the move was not visible in the September data.

Clearing profiles, for the record: Sep 30 softened only in the last 3 hours (0.94); Oct 2 and Oct 3 softened at 24–48 hours out (0.98 and 0.93, with 36–42% of sales below 0.9 × model) and then firmed on show day (1.05–1.25 in the final 12 hours). The location of the soft patch is not stable across shows.

## 2026-10-05 — Prediction set v2 frozen

Refit at 06:19 UTC on all data to that time (14,761 model-universe rows; 10,619 in the 90-day training window), same design, penalties and half-life as v1. File: `outputs/refit_oct5_model.json`. Grid: `outputs/forecast_and_buy_grid_refit_oct5.csv` — four reference seats (107 r10, 117 r15, 112 r15, 101 r20), pair, T−7 and T−1, for the 12 remaining shows, calendar drift frozen at zero.

Changes vs v1 worth recording: show effects for Oct 7/9/10/14/16/21/23 up 2–7 points, Oct 17 down 6; intercept +3.7%; calendar drift −5.6% per two weeks (was −6.9%); decay curve flatter at the front (30 d 1.13 vs 1.18). Last-7-day in-sample check: ratio 1.025, error 11.0%; Oct 7 still 1.10 — the smoothed fair value lags the hottest show by design.

Pre-registered claims for evaluation after Oct 31:

1. Show-day error (window construction as above) for the 12 remaining shows will have a median between 10% and 15%; the v1 window result of 7.8% will not be repeated on later dates without refitting.
2. Oct 30 and Oct 31 will clear above every other remaining date in the same seat cell, by at least 20%.
3. Saturdays (Oct 10, 17, 24) will clear above the adjacent Wednesdays by 15–30% in the same cell.
4. No remaining show will clear, as a whole, below 0.85 × the v2 model in the T−7 to T−1 window; mispricings will remain listing-level, at 9–21% of flow depending on the bar.
5. The Oct 7 ratio to v2 will fall back toward 1.00 by showtime (the rally will not extend into the last 48 hours).

## [after Oct 31] — v2 evaluation

To be appended.

# Perishable-Inventory Pricing and Calendar Relative Value in a 30-Maturity Event Market

**Harry Styles at Madison Square Garden, 30 shows, Aug 26 – Oct 31, 2026 — secondary-market pricing research.**

A fair-value model for resale tickets, validated out of sample, a set of trading rules built on it, and a live forward test that is still running. Written as a trading research project: the question throughout is not "what do prices look like" but "where, if anywhere, is there an edge after costs, and how would it be traded".

Status (Oct 5, 2026): v1 frozen. 16 shows played, 14 to go. Forward test runs to Oct 31; evaluation is logged in [`forward_test_log.md`](forward_test_log.md).

---

## 1. Why this market

The same artist plays the same building with the same seat map 30 times; only the date changes. That makes the residency a **term structure** rather than 30 separate events:

- a Wednesday vs a Saturday is a **calendar spread**;
- Oct 30–31 ("Harryween" and the finale) is a **seasonal premium**;
- the Oct 10–31 block went on sale five days after the rest, a **later issuance**.

The asset has properties a trader will recognise: a hard expiry (value goes to zero at showtime), a one-sided market (no way to short a later date), heavy and asymmetric transaction costs, and adverse selection (the cheapest listings are taken first by retail).

## 2. Data

| Source | What | Size |
| --- | --- | --- |
| SeatData transaction records | Timestamp, section, row, quantity, base price (before fees) of resale sales | 38,570 rows across 30 shows through Sep 29; refreshed exports for all 14 remaining shows through Oct 5 |
| Marketplace screenshots | Listing prices on SeatGeek, Gametime, TickPick | 1,118 observations; 16 SeatGeek checkouts used to measure the audience fee (14.6%) |
| Comparison residency | Backstreet Boys at Sphere, 21 shows | replication of the show-order effect |

Model scope: 100 Level, numbered sections 101–120, rows 3–22, sales before showtime — the deepest, most comparable segment. Pit, upper levels and bridges are excluded.

**Data policy.** Row-level SeatData records are licensed and are not in this repository. The repo contains code, protocols, coefficients, aggregated outputs and figures; `data/sample_200_rows.csv` documents the schema. Every number in this README traces to a file under `outputs/`.

## 3. The model

A fair-value surface for any 100 Level seat at any time before the show, fitted as a regression of log base price on six components:

```
ln P = intercept + row + front-row kicker + f(days to show) + calendar drift
       + section + section × row + show + quantity
```

- **Section** — 117 +52%, 107 +42% over the end sections; 116/118/106/108 +21–30%.
- **Row** — −13% per 10 rows back, plus a kicker for rows 3–6 (row 3 is +47% vs row 15).
- **Quantity** — singles −12%, pairs +7%, 3–4 seats +16%, 5+ +25% (vs unknown).
- **Time to show** — piecewise in log(days): 30 d 1.18, 14 d 1.00, 7 d 0.91, 1 d 0.79.
- **Show** — each date vs the opener: Wednesdays −18 to −29%, Saturdays −6 to +6%, Oct 31 +83%.
- **Calendar drift** — about −6% per two weeks in-sample; frozen at zero for forecasts.

Why logs: prices in this market move in percentages, not dollars; log form makes the effects additive, the errors proportional, and the price always positive. Worked example (Oct 10, section 107, row 10, pair, 7 days out): $247 base seat × 1.07 (row) × 1.18 (time) × 1.42 (section) × 1.06 (section × row) × 1.06 (show) × 1.07 (pair) ≈ **$537**.

Fit: Huber-type robust ridge (log residuals over 0.25 down-weighted), 90-day window, sample weights with a 14-day half-life, refit daily on data available that morning. Full formula and coefficients: `outputs/frozen_forecast_model.json` (Sep 29 freeze) and `outputs/refit_oct5_model.json`.

## 4. Validation

| Test | Sample | Model | Benchmark |
| --- | --- | --- | --- |
| Daily walk-forward replay, Sep 1–27 | 4,955 sales, each day priced with prior data only | MAE $61.6, median error 11.8% | Comparable-sales median: MAE $90.3, 18.3% — model won 27 of 27 days; 80% intervals covered 81% of held-out sales |
| Pre-registered window (coefficients frozen Sep 29 22:36 UTC) | Sep 30 show, 35 sales | median error 7.8%, MAE $36.6 | — |
| Frozen model, all sales Sep 30 – Oct 5 | 568 sales, 7 shows | median error 13.5%, median actual/model 1.07 | — |

The third row is the honest one: the frozen model held for shows inside 48 hours (Oct 2 and Oct 3 at 1.01) and under-priced the later shows by 10–25% as the market firmed in early October. A frozen fair value has a shelf life of about a week; the daily refit absorbs the move (see §6).

A negative result that belongs with the positive ones: the **change** in price over the next three days is not predictable — a "no change" forecast beat both candidate models (index-point MAE 7.25 vs 8.13 and 8.15). The surface prices the cross-section; the time dimension is close to a random walk at a three-day horizon.

## 5. Findings

1. **Prices decay into the show.** −21% from 14 days out to 1 day out, steady rather than a cliff. Raw data for the first 15 shows: the last 12 hours clear 28% below the 7–30 day level (12% after calendar controls). Holding into show week is a losing position by construction.
2. **Later shows are cheaper, but not monotonically.** −18% per 10 shows in performance order (95% CI −26% to −9%), Saturdays +14%, Wednesdays −4%, Halloween finale +83%. The path is a sawtooth drifting down: the drift is supply (30 × ~19,000 seats in one city), the teeth are demand. For a buyer the calendar is a bigger risk than the countdown. Identification caveat: show order, calendar time and a Sep 10 tour announcement cannot be separated inside one residency; with an announcement control the estimate is −12% with an interval through zero.
3. **Seat structure is stable and well priced.** Centre of the long sides (117, 107) is the money; row 3 is +47% over row 15; singles clear ~18% below pairs, so a cheap single is not cheap and splitting a pair destroys value. Row tiers: 3–5 carry the premium and the widest dispersion; rows 6–22 are a smooth slope of 1–3% per row.
4. **Volume comes late, the discount is unreliable.** Sales concentrate in the final 2–3 days without a price collapse. Where the soft patch sits moves from show to show: Sep 30 in the last 3 hours (0.94 × model), Oct 2–3 at 24–48 hours out (0.93–0.98, 36–42% of sales below 0.9 × model) followed by a firm show day (1.05–1.25). Waiting for a late fire sale is not a strategy.
5. **No momentum.** A naive three-day reversal (β = −0.49) was a shared-endpoint artefact; splitting the endpoint gave −0.14 (interval through zero), non-overlapping windows +0.04.
6. **Regime note (Oct 5).** Between Sep 30 and Oct 5 the early-October Wednesday discount compressed from −25% to roughly −7% relative to the opener, with volume rising on the later dates. No artist-specific catalyst was found; the working hypothesis is demand spilling from sold-down early-October dates into later ones. Unrelated to equity markets: the move is date-specific, not level-wide, and a week is the wrong horizon for a wealth effect.

## 6. Trading rules

Full text in [`trading_rules.md`](trading_rules.md). The short version, on the broker cost structure (3% to buy, 3.5% to sell; the audience's 14.6% marketplace fee is not our cost):

- **Maximum buy price = 0.852 × model fair value** for a 10% return; 0.937 is break-even; never above it.
- **Main rule: buy at or below 0.85 × M.** At a 10% wholesale discount this earns 10% if sold to the audience at model price and breaks even if dumped to another broker.
- List the same day at model price; markdown rule until a fill model exists: unsold at T−3 → 0.95, T−1 → 0.90, never into show day.
- Prefer odd lots of three and unknown-quantity listings (below the 5%-return bar 22–25% of the time vs 8% for pairs); premium sections for liquidity, not because they are mispriced more often.
- Size to the opportunity, not the budget: qualifying listings are 9–21% of flow depending on the bar — a few tickets a day across all remaining shows.

Two parameters are deliberately left open and labelled: the wholesale discount *d* on broker-to-broker exits, and the fill probability *p* of a listing at model price. Both need listing-level data that becomes available in the trial period.

## 7. Forward test

Two pre-registered prediction sets, both committed before the outcomes:

| Set | Frozen | Covers | Evaluation |
| --- | --- | --- | --- |
| v1 | Sep 29 22:36 UTC | Sep 30 show window; Sep 30 – Oct 5 sales | logged — 7.8% on the window, 13.5% over the week, systematic under-pricing of later shows |
| v2 | Oct 5 06:19 UTC (`outputs/forecast_and_buy_grid_refit_oct5.csv`) | 12 remaining shows, four reference seats, T−7 and T−1 | after Oct 31 |

## 8. Limitations and next steps

- **Scope.** 100 Level, rows 3–22, one residency. Nothing here is a claim about ticket markets in general; the Backstreet Boys check supports the direction of the order effect only.
- **Sales only, no supply.** The data records transactions, not active listings, so fill probability and days-on-market are unknown — the largest gap for turning the pricing surface into a trading system.
- **Half-life.** The 14-day half-life makes the fair value lag a fast-moving show by about a week (Oct 7 still traded 10% above the Oct 5 refit). A 7-day half-life is the first thing to test in the daily replay.
- **Cross-section and competing events.** Whether 200 Level / floor prices move 100 Level prices, and whether other New York events on the same night matter, are the two extensions planned for v2.
- **No face values.** Primary prices were not collected, so the share of resale trades clearing below face cannot be computed.

## 9. Repository map

| Path | Content |
| --- | --- |
| `01_lead_time/` | Time-to-show price index, first 15 shows |
| `02_momentum/` | Three-day momentum tests and the endpoint artefact |
| `03_bsb_comparison/` | Backstreet Boys at Sphere replication |
| `04_later_shows/` | Show-order effect with weekday controls |
| `05_seat_groups/` | MSG 100 Level section groups and row bands |
| `06_price_model_v1/` | Model, daily replay, benchmark comparison |
| `07_sales_update/` | Data reconciliation and the Sep 29 frozen model |
| `08_09_quotes/` | Cross-platform listing observations and fee measurement (stages 08 and 09) |
| `10_refit_oct5/` | Oct 5 refit, forecast and buy-price grids |
| `trading_rules.md` | Rules, cost structure, open parameters |
| `forward_test_log.md` | Dated record of predictions and outcomes |
| `outputs/` | Coefficients, grids, out-of-sample summaries, key figures |
| `reports/` | The Oct 1 report written for the employer |
| `data/` | 200-row schema sample only |

Stage reports under `01`–`09` are written in Chinese; this README and the two root documents are the English summary. Stage folders were renamed for this release, so paths inside the stage reports refer to the original working names and to `raw/`, `input/` and `upstream/` directories that hold licensed data and are not included.

`reports/2026-10-01_pricing_report_v1.pdf` is the Oct 1 report written for the employer; its cost assumptions (a 29% round trip) were superseded on Oct 5 by the broker cost structure in `trading_rules.md`.

## 10. Reproducing

```
pip install numpy pandas scipy
python 06_price_model_v1/model_v1.py        # daily replay and benchmark
python 07_sales_update/update.py           # reconcile new exports, refit, freeze
python 10_refit_oct5/refit.py --master <sep29 master> --exports <export dir> --frozen outputs/frozen_forecast_model.json --out outputs
```

Scripts expect the licensed row-level exports at the paths named in each file; `data/sample_200_rows.csv` documents the schema. Without the exports the numbers cannot be reproduced; every number in this README is nonetheless traceable to a committed file under `outputs/` or a stage folder.

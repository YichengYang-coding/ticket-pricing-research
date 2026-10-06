# Trading rules — Harry Styles MSG residency, v1 (frozen Oct 5, 2026)

These rules turn the fair-value model into decisions. Every number is relative to **M**, the model fair value of the exact cell being traded: section × row × quantity × expected sale date. All prices are base prices before marketplace fees. Rules are stated so they can be checked; where a parameter is unknown it is named, not guessed.

## 1. Cost structure

We trade as a broker, into the market (audience via marketplaces) and with other brokers.

| Leg | Cost | Source |
| --- | --- | --- |
| Buy from brokers or platforms | +3% on the price paid | employer |
| Sell to the audience through a marketplace | we receive 96.5% of the base price we list | employer (0.96–0.97) |
| Sell to another broker | we receive ~97% of the wholesale price W | employer; W itself unknown (see §7) |
| Audience marketplace fee | 14.6% on top of base (SeatGeek, measured on 16 checkouts) | not our cost; affects demand only |

Round trip through the audience channel: about 6.5%.

A listing price seen on a marketplace as a buyer is all-in; divide by 1.146 to get the base price before comparing it with M or with transaction data.

## 2. Buy limits

Formula: **maximum buy price ÷ M = (1 − selling cost) ÷ [(1 + target return) × (1 + buying cost)]**

| Exit | Target return | Max buy ÷ M |
| --- | --- | --- |
| Audience at M | 15% | 0.815 |
| Audience at M | 10% | 0.852 |
| Audience at M | 5% | 0.892 |
| Audience at M | 0% (break-even) | 0.937 |
| Broker at W = 0.95 M | 0% | 0.895 |
| Broker at W = 0.90 M | 0% | 0.847 |
| Broker at W = 0.85 M | 0% | 0.800 |

**Main rule: buy at or below 0.85 × M.** If the wholesale discount is 10%, this earns 10% when sold to the audience at M and breaks even when dumped to a broker. If the wholesale discount turns out larger than 10%, lower the bar to the matching broker-exit row.

Never buy above 0.937 × M under any framing: at that price the round trip is lost even with a perfect resale.

## 3. What to look for

Observed frequency of trades at or below each bar, 568 sales Sep 30 – Oct 5 against the frozen model (a lower bound, since the market firmed after the freeze):

| Bar | Share of trades at or below |
| --- | --- |
| 0.937 (break-even) | 21% |
| 0.892 (5%) | 14% |
| 0.852 (10%) | 9% |

By lot size, share at or below 0.892: odd lots of three 25%, unknown quantity 22%, singles 18%, pairs 8%, fours 4%. By location: premium sections (106–108, 115–119) 18%, others 11%.

Priorities, in order:

1. Odd lots of three and unknown-quantity listings — mispriced two to three times as often as pairs.
2. Premium sections — for resale liquidity, not because they are mispriced more often.
3. Shows with the deepest flow in the next 48 hours — most catchable listings in absolute terms.

Avoid: singles that merely look cheap (they resell ~18% below pairs; the model already prices this), and anything above 0.937 × M.

## 4. Listing and markdown

- List the same day at **1.00 × M** (0.97 × M if the aim is to move within a few days).
- Unsold at T−3 → 0.95 × M. Unsold at T−1 → 0.90 × M. Never carry inventory into show day; if still unsold at T−1 evening, exit to a broker at W.
- Each day held near the show costs 1–2% from the decay curve; the return is earned by turning quickly.
- Inventory marked above 1.10 × M by the market: list at market, do not chase it down. Above 1.25 × M: sell actively. (Rule revised Oct 5 after Oct 7 ran from 1.15 to 1.37 × M in a week — a flat "sell at 1.10" rule was right on expectation and wrong ex post.)

## 5. Risk limits

- Per show: no more than 15% of the budget.
- Per listing: no more than 4 tickets unless the listing is an odd lot being completed into pairs.
- Total deployed: sized to the number of qualifying listings, never to the budget. Unspent capital is the expected outcome on an event where no show trades below fair value.
- Time stop: anything bought is either sold or exited to a broker by T−1 evening, without exception.

## 6. Fair value maintenance

- Refit daily with the pipeline (robust ridge, 90-day window, 14-day half-life). A frozen fit is for evaluation only; its shelf life as a trading reference is about one week.
- Keep the model's calendar-drift term at zero when forecasting more than a few days ahead; extrapolating it is the single largest source of grid error.
- Known lag: a show whose price moves 20%+ in a week will sit 5–10% away from the refit model for several days. Treat a persistent ratio above 1.10 as "rich, do not buy", not as a model error to be overridden.

## 7. Open parameters (to calibrate in the trial period)

| Parameter | What it is | Why it matters | How to get it |
| --- | --- | --- | --- |
| **d** — wholesale discount | How far below M a broker-to-broker sale clears | Sets the floor of the buy bar (§2) | Employer's own broker sales vs same-day retail base |
| **p** — fill probability | Chance a listing at 1.00 × M sells within 1, 3, 7 days | Converts the markdown rule into an expected exit price | Listing-level data: active listings, price changes, delistings |
| Half-life | 14 days now; 7 days may track regime moves faster | Trade-off between lag and noise | Daily replay with both settings |

Until d and p are measured, the main rule (≤ 0.85 × M) is the conservative setting: it does not depend on p, and it breaks even for d up to 10%.

## 8. What the rules are not

They are not a forecast of profit. On the 2026 residency the base case at market prices is to pass; the edge, where it exists, is a few mispriced listings a day. A realistic month is the budget turned about once at a 5–10% margin.

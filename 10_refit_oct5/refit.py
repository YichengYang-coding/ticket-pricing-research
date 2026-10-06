"""Oct 5 refit of the 100 Level fair-value model and the v2 forecast / buy-price grids.

Same design, penalties, robust weighting and 14-day half-life as 06_price_model_v1/model_v1.py
and the Sep 29 frozen fit in 07_sales_update/model_v1_frozen.py. The only change is the data:
the Sep 29 master is merged with fresh SeatData exports for the 15 shows from Sep 30 onward
(each fresh export replaces that show's rows in the master).

Inputs (licensed row-level data, not in this repository):
    --master   Harry_current_sales_20260929.csv  (07_sales_update output, Sep 29 master)
    --exports  directory of SeatData exports named <MMDD>.csv or hs<MMDD>.csv, columns
               date_time, source, zone, section, row, quantity, price

Outputs (written to --out):
    refit_oct5_model.json                 coefficients, origin, event list
    event_effects_frozen_vs_refit.csv     show effects, frozen v1 vs this refit
    forecast_and_buy_grid_refit_oct5.csv  model price, max buy (10%), break-even for four
                                          reference seats, T-7 and T-1, remaining shows

Run:  python 10_refit_oct5/refit.py --master <path> --exports <dir> --frozen outputs/frozen_forecast_model.json --out outputs
"""
import argparse, json, re, os
import numpy as np, pandas as pd
from scipy.linalg import solve

SECTIONS = list(range(101, 121))
QUANTITIES = ['unknown', '1', '2', '3', '4', '5plus']
REF_SEATS = [(107, 10), (117, 15), (112, 15), (101, 20)]
BUY_10PCT, BUY_5PCT, BREAKEVEN = 0.852, 0.892, 0.937   # broker costs: 3% to buy, 3.5% to sell


def load_master(path):
    m = pd.read_csv(path, low_memory=False)
    m = m[m.included_in_research.eq(True) & m.source.eq('sh') & m.zone.eq('100 Level')
          & m.section_numeric.between(101, 120) & m.row_numeric.between(3, 22)
          & m.price_usd_base.gt(0) & m.at_or_after_start.eq(False)].copy()
    out = pd.DataFrame({'event': m.event_date.astype(str),
                        'ts': pd.to_datetime(m.observed_at_utc, utc=True),
                        'event_start': pd.to_datetime(m.event_start_utc, utc=True),
                        's': m.section_numeric.astype(int), 'r': m.row_numeric.astype(int),
                        'q': m.qty_group.astype(str).replace({'5+': '5plus'}),
                        'price': m.price_usd_base.astype(float)})
    return out


def load_export(path, event):
    r = pd.read_csv(path)
    r.columns = ['dt', 'source', 'zone', 'section', 'row', 'qty', 'price']
    # SeatData export timestamps are fixed UTC-4 (ET daylight time), as in the earlier stages
    r['ts'] = pd.to_datetime(r.dt, format='%m-%d-%y / %I:%M %p').dt.tz_localize('Etc/GMT+4').dt.tz_convert('UTC')
    r['event_start'] = pd.Timestamp(event + ' 20:00', tz='America/New_York').tz_convert('UTC')
    r['price'] = pd.to_numeric(r.price, errors='coerce')
    r = r[r.source.eq('sh') & r.zone.eq('100 Level')].copy()
    r['s'] = pd.to_numeric(r.section, errors='coerce'); r['r'] = pd.to_numeric(r.row, errors='coerce')
    r = r[r.s.between(101, 120) & r.r.between(3, 22) & r.price.gt(0) & r.ts.lt(r.event_start)].copy()
    r['s'] = r.s.astype(int); r['r'] = r.r.astype(int)
    qn = pd.to_numeric(r.qty, errors='coerce').fillna(0).astype(int)
    r['q'] = np.select([qn.eq(0), qn.eq(1), qn.eq(2), qn.eq(3), qn.eq(4)], ['unknown', '1', '2', '3', '4'], '5plus')
    r['event'] = event
    return r[['event', 'ts', 'event_start', 's', 'r', 'q', 'price']]


def design(f, origin, events):
    n = len(f); cols = {'intercept': np.ones(n)}; pen = [1e-8]
    def add(name, arr, lam): cols[name] = np.asarray(arr, float); pen.append(lam)
    add('row_slope', (f.r - 15) / 10, 1)
    add('front_extra', np.maximum(6 - f.r, 0) / 3, 1)
    lead = (f.event_start - f.ts).dt.total_seconds().to_numpy() / 86400
    u = np.log1p(np.maximum(lead, 0)); add('log_days', u, 1)
    for knot in [1, 4, 7, 14, 30]: add('log_days_hinge_%d' % knot, np.maximum(u - np.log1p(knot), 0), 1)
    add('calendar_trend', (f.ts - origin).dt.total_seconds().to_numpy() / 86400 / 14, 1)
    for s in SECTIONS[1:]: add('section_%d' % s, f.s.eq(s), 2)
    for e in events[1:]: add('event_' + e, f.event.eq(e), 3)
    for q in QUANTITIES[1:]: add('quantity_' + q, f.q.eq(q), 2)
    for s in SECTIONS[1:]: add('section_row_%d' % s, f.s.eq(s) * (f.r - 15) / 10, 20)
    return np.column_stack(list(cols.values())), list(cols), np.asarray(pen)


def fit(train, origin, events):
    X, names, pen = design(train, origin, events); y = np.log(train.price.to_numpy())
    age = (origin - train.ts).dt.total_seconds().to_numpy() / 86400
    base = np.exp2(-age / 14); base *= len(base) / base.sum()
    b = np.zeros(X.shape[1]); b[0] = np.median(y)
    for it in range(30):
        err = y - X @ b
        w = base * np.minimum(1, .25 / np.maximum(abs(err), 1e-12))     # Huber-type down-weighting
        gram = X.T @ (X * w[:, None]) + np.diag(pen)
        bn = solve(gram, X.T @ (w * y), assume_a='pos')
        if max(abs(bn - b)) < 1e-6: b = bn; break
        b = bn
    return dict(zip(names, b)), it + 1


def predict(c, events, event, s, r, q, lead_days):
    x = c['intercept'] + c['row_slope'] * (r - 15) / 10 + c['front_extra'] * max(6 - r, 0) / 3
    u = np.log1p(max(lead_days, 0)); x += c['log_days'] * u
    for k in [1, 4, 7, 14, 30]: x += c['log_days_hinge_%d' % k] * max(u - np.log1p(k), 0)
    if s != 101: x += c['section_%d' % s] + c['section_row_%d' % s] * (r - 15) / 10
    if event != events[0]: x += c['event_' + event]
    if q != 'unknown': x += c['quantity_' + q]
    return float(np.exp(x))          # calendar drift held at zero for forecasts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--master', required=True); ap.add_argument('--exports', required=True)
    ap.add_argument('--frozen', required=True); ap.add_argument('--out', default='outputs')
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)

    master = load_master(a.master)
    fresh = []
    for f in sorted(os.listdir(a.exports)):
        m = re.match(r'(?:hs)?(\d{2})(\d{2})\.csv$', f)
        if m: fresh.append(load_export(os.path.join(a.exports, f), '2026-%s-%s' % (m.group(1), m.group(2))))
    fresh = pd.concat(fresh, ignore_index=True)
    d = pd.concat([master[~master.event.isin(fresh.event.unique())], fresh], ignore_index=True).sort_values('ts').reset_index(drop=True)
    events = sorted(d.event.unique()); origin = d.ts.max()
    train = d[d.ts.ge(origin - pd.Timedelta(days=90))]
    c, iters = fit(train, origin, events)
    print('rows', len(d), 'train', len(train), 'origin', origin, 'iterations', iters)
    json.dump({'origin_utc': str(origin), 'events': events, 'coefficients': c, 'training_rows': len(train)},
              open(os.path.join(a.out, 'refit_oct5_model.json'), 'w'), indent=1)

    fz = json.load(open(a.frozen))['coefficients']
    ev = pd.DataFrame({'event': events, 'weekday': [pd.Timestamp(e).day_name()[:3] for e in events],
                       'frozen_pct': [round(100 * (np.exp(fz.get('event_' + e, 0)) - 1)) for e in events],
                       'refit_pct': [round(100 * (np.exp(c.get('event_' + e, 0)) - 1)) for e in events]})
    ev['change_pts'] = ev.refit_pct - ev.frozen_pct
    ev.to_csv(os.path.join(a.out, 'event_effects_frozen_vs_refit.csv'), index=False)

    rows = []
    for e in [x for x in events if pd.Timestamp(x) >= origin.tz_convert('America/New_York').normalize().tz_localize(None)]:
        for (s, r) in REF_SEATS:
            for L in [7, 1]:
                m = predict(c, events, e, s, r, '2', L)
                rows.append({'event': e, 'wd': pd.Timestamp(e).day_name()[:3], 'section': s, 'row': r, 'lead_days': L,
                             'refit_model': m, 'frozen_model': predict(fz, events, e, s, r, '2', L),
                             'max_buy_10pct': BUY_10PCT * m, 'max_buy_5pct': BUY_5PCT * m, 'breakeven': BREAKEVEN * m})
    pd.DataFrame(rows).round(1).to_csv(os.path.join(a.out, 'forecast_and_buy_grid_refit_oct5.csv'), index=False)
    print('written to', a.out)


if __name__ == '__main__':
    main()

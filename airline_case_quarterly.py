"""Full-quarter BTS DB1BMarket case study, 2007 Q1 through 2015 Q4.

An illustrative merger retrospective with explicit pretrend diagnostics. All
reported fare contrasts are descriptive; the matched controls are imperfect.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd

from data_paths import quarter_file

HERE = Path(__file__).resolve().parent
DATA = HERE / "db1b_aggregated"
OUT = HERE / "airline_case_quarterly_results"
OUT.mkdir(exist_ok=True)
QUARTERS = [(year, quarter) for year in range(2007, 2016) for quarter in range(1, 5)]
KEYS = [f"{y}Q{q}" for y, q in QUARTERS]
RNG = np.random.default_rng(20260921)

cells = {}
markets = {}
presence = []
for year, quarter in QUARTERS:
    key = f"{year}Q{quarter}"
    d = pd.read_csv(quarter_file(DATA, year, quarter))
    assert d.Year.eq(year).all() and d.Quarter.eq(quarter).all()
    d["share"] = d.passengers / d.groupby("route").passengers.transform("sum")
    cells[key] = d
    m = d.groupby("route").agg(
        passengers=("passengers", "sum"),
        weighted_fare=("fare_x_pax", "sum"),
        weighted_distance=("distance_x_pax", "sum"),
    )
    m["fare"] = m.weighted_fare / m.passengers
    m["distance"] = m.weighted_distance / m.passengers
    m["hhi"] = d.groupby("route").share.apply(lambda s: float(np.square(s).sum()))
    m["active_carriers"] = d[d.passengers >= 50].groupby("route").carrier.nunique().reindex(m.index).fillna(0)
    markets[key] = m
    presence.append(set(m.index))

balanced = set.intersection(*presence)
base = cells["2009Q2"]
material = base[base.passengers >= 50].groupby("route").carrier.agg(set)
all_carriers = base.groupby("route").carrier.agg(set)
overlap_candidates = set(material[material.map(lambda s: "WN" in s and "FL" in s)].index)
fl_candidates = set(material[material.map(lambda s: "FL" in s)].index)
fl_only_candidates = {route for route in fl_candidates if "WN" not in all_carriers[route]}
other_lcc = {"B6", "F9", "NK", "VX", "G4"}
lcc_candidates = {
    route for route, s in material.items()
    if len(s) >= 2 and bool(s & other_lcc) and not bool(all_carriers[route] & {"WN", "FL"})
}
treated = sorted(overlap_candidates & balanced)
fl_only = sorted(fl_only_candidates & balanced)
lcc = sorted(lcc_candidates & balanced)
if len(treated) < 15:
    raise ValueError(f"Only {len(treated)} balanced overlap routes remain")

florida_airports = {"MCO", "FLL", "TPA", "PBI", "RSW", "JAX", "MIA", "SRQ", "DAB", "EYW", "PNS", "TLH"}
def florida_route(route):
    return bool(set(route.split("-")) & florida_airports)

def early_route_slope(routes):
    """Fare trend using 2007Q1-2009Q2 only; later preperiod is held out."""
    names = [f"{y}Q{q}" for y, q in QUARTERS if (y, q) <= (2009, 2)]
    time = np.arange(len(names), dtype=float)
    season = np.array([int(k[-1]) for k in names])
    x = np.column_stack([np.ones(len(time)), time] + [(season == q).astype(float) for q in (2, 3, 4)])
    y = np.array([[np.log(markets[k].loc[route, "fare"]) for k in names] for route in routes])
    slopes = (np.linalg.pinv(x) @ y.T)[1, :]
    return pd.Series(slopes, index=routes)

def match(controls, florida_exact, include_early_slope=False):
    pool = treated + controls
    f = markets["2009Q2"].loc[pool]
    features = pd.DataFrame({
        "log_fare": np.log(f.fare),
        "log_passengers": np.log(f.passengers),
        "log_distance": np.log(f.distance),
        "hhi": f.hhi,
    }, index=f.index)
    if include_early_slope:
        features["early_pre_slope"] = early_route_slope(pool)
    sd = features.std(ddof=0)
    z = (features - features.mean()) / sd
    edges = sorted(
        (float(np.linalg.norm(z.loc[t].values - z.loc[c].values)), t, c)
        for t in treated for c in controls
        if not florida_exact or florida_route(t) == florida_route(c)
    )
    pairs, used_t, used_c = [], set(), set()
    for distance, t, c in edges:
        if distance > 2.5:
            break
        if t not in used_t and c not in used_c:
            pairs.append((t, c, distance))
            used_t.add(t)
            used_c.add(c)
    if len(pairs) < 8:
        raise ValueError(f"Only {len(pairs)} matched pairs")
    tmat = features.loc[[p[0] for p in pairs]].reset_index(drop=True)
    cmat = features.loc[[p[1] for p in pairs]].reset_index(drop=True)
    # Standardized difference in the conventional form, sqrt((s_T^2 + s_C^2)/2).
    # Dividing by the SD of the pooled candidate pool instead - as an earlier
    # version of this script did - inflates the denominator with between-group
    # and unmatched-control variance and makes balance look better than it is.
    balance = ((tmat.mean() - cmat.mean())
               / np.sqrt((tmat.var(ddof=1) + cmat.var(ddof=1)) / 2)).to_dict()
    return pairs, balance

main_pairs, main_balance = match(fl_only, florida_exact=True)
lcc_pairs, lcc_balance = match(lcc, florida_exact=False)
lcc_florida_pairs, lcc_florida_balance = match(lcc, florida_exact=True)
trend_pairs, trend_balance = match(fl_only, florida_exact=True, include_early_slope=True)

def gaps(pairs):
    return np.array([
        [np.log(markets[key].loc[t, "fare"]) - np.log(markets[key].loc[c, "fare"])
         for t, c, _ in pairs]
        for key in KEYS
    ]).T  # pair x quarter

gap_main = gaps(main_pairs)
gap_lcc = gaps(lcc_pairs)
gap_lcc_florida = gaps(lcc_florida_pairs)
gap_trend = gaps(trend_pairs)

BASE = ["2009Q3", "2009Q4", "2010Q1", "2010Q2"]  # four seasons, before announcement
PRE_EARLY = ["2007Q3", "2007Q4", "2008Q1", "2008Q2"]
PRE_LATE = ["2008Q3", "2008Q4", "2009Q1", "2009Q2"]

def mean_window(gap, names):
    return gap[:, [KEYS.index(name) for name in names]].mean(axis=1)

def summarize(log_diffs):
    values = np.asarray(log_diffs, dtype=float)
    draws = RNG.choice(values, size=(10000, len(values)), replace=True).mean(axis=1)
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return {
        "n_pairs": int(len(values)),
        "log_difference": float(values.mean()),
        "percent": float(100 * np.expm1(values.mean())),
        "ci_low_percent": float(100 * np.expm1(lo)),
        "ci_high_percent": float(100 * np.expm1(hi)),
    }

def window_contrasts(gap):
    base = mean_window(gap, BASE)
    windows = {
        "early_pre": PRE_EARLY,
        "late_pre": PRE_LATE,
        "base": BASE,
        **{str(y): [f"{y}Q{q}" for q in range(1, 5)] for y in range(2011, 2016)},
        "2015_H1": ["2015Q1", "2015Q2"],
    }
    return {name: summarize(mean_window(gap, keys) - base) for name, keys in windows.items()}

main = window_contrasts(gap_main)
alt_lcc = window_contrasts(gap_lcc)
alt_lcc_florida = window_contrasts(gap_lcc_florida)
alt_trend = window_contrasts(gap_trend)
main_alt_baseline = summarize(
    mean_window(gap_main, [f"2015Q{q}" for q in range(1, 5)])
    - mean_window(gap_main, PRE_LATE)
)
placebo = summarize(mean_window(gap_main, BASE) - mean_window(gap_main, PRE_EARLY))
trend_match_holdout = summarize(mean_window(gap_trend, BASE) - mean_window(gap_trend, PRE_LATE))

pre_keys = [f"{y}Q{q}" for y, q in QUARTERS if (y, q) <= (2010, 2)]
pre_gap = gap_main[:, [KEYS.index(name) for name in pre_keys]]
time = np.arange(len(pre_keys), dtype=float)
season = np.array([int(k[-1]) for k in pre_keys])
x = np.column_stack([np.ones(len(time)), time] + [(season == q).astype(float) for q in (2, 3, 4)])
slopes = (np.linalg.pinv(x) @ pre_gap.T)[1, :]
pretrend_annualized = summarize(4 * slopes)

rolling = []
for i, key in enumerate(KEYS):
    if i < 3:
        continue
    row = {"period": key, "year": int(key[:4]), "quarter": int(key[-1])}
    for name, gap in [("main", gap_main), ("other_lcc", gap_lcc), ("other_lcc_florida", gap_lcc_florida)]:
        x = gap[:, i-3:i+1].mean(axis=1) - mean_window(gap, BASE)
        value = summarize(x)
        row[f"{name}_percent"] = value["percent"]
        row[f"{name}_ci_low"] = value["ci_low_percent"]
        row[f"{name}_ci_high"] = value["ci_high_percent"]
    rolling.append(row)

def structure(pairs):
    hhi, active, pax = [], [], []
    for t, c, _ in pairs:
        for array, col, transform in [
            (hhi, "hhi", lambda x: x),
            (active, "active_carriers", lambda x: x),
            (pax, "passengers", np.log),
        ]:
            pre_t = np.mean([transform(markets[k].loc[t, col]) for k in BASE])
            pre_c = np.mean([transform(markets[k].loc[c, col]) for k in BASE])
            post_t = np.mean([transform(markets[f"2015Q{q}"].loc[t, col]) for q in range(1, 5)])
            post_c = np.mean([transform(markets[f"2015Q{q}"].loc[c, col]) for q in range(1, 5)])
            array.append((post_t - pre_t) - (post_c - pre_c))
    return {"hhi_difference": float(np.mean(hhi)),
            "active_carrier_difference": float(np.mean(active)),
            "sampled_passenger_change": summarize(pax)}

result = {
    "title": "Southwest-AirTran full quarterly overlap-route comparison",
    "source": "BTS DB1BMarket carrier-ticket records, every quarter 2007Q1-2015Q4",
    "quarters": len(KEYS),
    "preannouncement_window": BASE,
    "overlap_candidates_2009Q2": len(overlap_candidates),
    "balanced_overlap_routes": len(treated),
    "balanced_control_candidates": {"airtran_only": len(fl_only), "other_lcc": len(lcc)},
    "pairs": {"main": len(main_pairs), "other_lcc": len(lcc_pairs),
              "early_pretrend_matched": len(trend_pairs),
              "other_lcc_florida_exact": len(lcc_florida_pairs)},
    "balance": {"main": main_balance, "other_lcc": lcc_balance,
                "early_pretrend_matched": trend_balance},
    "main": main,
    "other_lcc": alt_lcc,
    "other_lcc_florida_exact": alt_lcc_florida,
    "early_pretrend_matched": alt_trend,
    "early_pretrend_match_holdout_preperiod": trend_match_holdout,
    "placebo_early_to_base": placebo,
    "pretrend_annualized_percent": pretrend_annualized,
    "main_2015_vs_earlier_baseline": main_alt_baseline,
    "market_structure": structure(main_pairs),
    "interpretation": "Descriptive; check pretrend, comparator sensitivity, and post-survival selection before any causal claim.",
}
(OUT / "results.json").write_text(json.dumps(result, indent=2))
pd.DataFrame(main_pairs, columns=["overlap_route", "airtran_only_control", "match_distance"]).to_csv(OUT / "matched_routes.csv", index=False)
pd.DataFrame(lcc_pairs, columns=["overlap_route", "other_lcc_control", "match_distance"]).to_csv(OUT / "other_lcc_matched_routes.csv", index=False)
pd.DataFrame(trend_pairs, columns=["overlap_route", "pretrend_matched_control", "match_distance"]).to_csv(OUT / "pretrend_matched_routes.csv", index=False)
pd.DataFrame(rolling).to_csv(OUT / "quarterly_path.csv", index=False)
pd.DataFrame([{"window": k, **v} for k, v in main.items()]).to_csv(OUT / "window_estimates.csv", index=False)
print(json.dumps({"candidates": result["overlap_candidates_2009Q2"], "balanced_overlap": len(treated),
                  "pairs": result["pairs"], "pretrend": pretrend_annualized,
                  "placebo": placebo, "main_2015": main["2015"],
                  "other_lcc_2015": alt_lcc["2015"],
                  "lcc_florida_2015": alt_lcc_florida["2015"],
                  "pretrend_matched_2015": alt_trend["2015"],
                  "holdout_pretrend": trend_match_holdout}, indent=2))

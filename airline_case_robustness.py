"""Additional checks: all itineraries, connecting share, and route influence.

The comparison uses the already declared matched pairs. It never treats the
supplemental specifications as a causal estimate of the merger.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd

from data_paths import quarter_file

HERE = Path(__file__).resolve().parent
ALL = HERE / "db1b_all_itineraries"
DIRECT = HERE / "db1b_aggregated"
OUT = HERE / "airline_case_quarterly_results"
QUARTERS = [(y, q) for y in range(2007, 2016) for q in range(1, 5)]
KEYS = [f"{y}Q{q}" for y, q in QUARTERS]
BASE = ["2009Q3", "2009Q4", "2010Q1", "2010Q2"]
POST = [f"2015Q{q}" for q in range(1, 5)]
RNG = np.random.default_rng(20260921)

pair_files = {
    "main": ("matched_routes.csv", "airtran_only_control"),
    "other_lcc": ("other_lcc_matched_routes.csv", "other_lcc_control"),
    "early_pretrend_matched": ("pretrend_matched_routes.csv", "pretrend_matched_control"),
}
pairs = {name: list(pd.read_csv(OUT / filename)[["overlap_route", control]].itertuples(index=False, name=None))
         for name, (filename, control) in pair_files.items()}
routes = set(r for group in pairs.values() for t, c in group for r in (t, c))

all_markets = {}
direct_markets = {}
for year, q in QUARTERS:
    key = f"{year}Q{q}"
    d = pd.read_csv(quarter_file(ALL, year, q))
    d = d[d.route.isin(routes)]
    m = d.groupby("route").agg(passengers=("passengers", "sum"),
                               fare_x_pax=("fare_x_pax", "sum"))
    m["fare"] = m.fare_x_pax / m.passengers
    direct_pax = d[d.trip_type == "nonstop"].set_index("route").passengers
    m["nonstop_share"] = direct_pax.reindex(m.index).fillna(0) / m.passengers
    all_markets[key] = m
    f = pd.read_csv(quarter_file(DIRECT, year, q))
    f = f[f.route.isin(routes)].groupby("route").agg(passengers=("passengers", "sum"),
                                                    fare_x_pax=("fare_x_pax", "sum"))
    f["fare"] = f.fare_x_pax / f.passengers
    direct_markets[key] = f

def pair_window(group, markets, field, window):
    out = []
    for t, c in group:
        a = []
        for key in window:
            if t not in markets[key].index or c not in markets[key].index:
                raise ValueError(f"Missing route {t} or {c} in {key}")
            tv, cv = markets[key].loc[t, field], markets[key].loc[c, field]
            a.append(np.log(tv) - np.log(cv) if field == "fare" else tv - cv)
        out.append(float(np.mean(a)))
    return np.array(out)

def summary(values, percent=True):
    values = np.asarray(values, dtype=float)
    draw = RNG.choice(values, size=(10000, len(values)), replace=True).mean(axis=1)
    mean = float(values.mean())
    lo, hi = np.percentile(draw, [2.5, 97.5])
    if percent:
        mean, lo, hi = 100*np.expm1([mean,lo,hi])
    else:
        mean, lo, hi = 100*np.array([mean,lo,hi])
    return {"n_pairs": len(values), "estimate": float(mean),
            "ci_low": float(lo), "ci_high": float(hi)}

output = {"all_itinerary_fare_2015": {}, "nonstop_share_2015_percentage_points": {},
          "direct_fare_replication": {}, "all_itinerary_pretrend_annualized": {}}
for name, group in pairs.items():
    delta = pair_window(group, all_markets, "fare", POST) - pair_window(group, all_markets, "fare", BASE)
    output["all_itinerary_fare_2015"][name] = summary(delta)
    share = pair_window(group, all_markets, "nonstop_share", POST) - pair_window(group, all_markets, "nonstop_share", BASE)
    output["nonstop_share_2015_percentage_points"][name] = summary(share, percent=False)
    direct = pair_window(group, direct_markets, "fare", POST) - pair_window(group, direct_markets, "fare", BASE)
    output["direct_fare_replication"][name] = summary(direct)
    pre_keys = [f"{y}Q{q}" for y, q in QUARTERS if (y, q) <= (2010, 2)]
    t = np.arange(len(pre_keys), dtype=float)
    season = np.array([int(key[-1]) for key in pre_keys])
    x = np.column_stack([np.ones(len(t)), t] + [(season == q).astype(float) for q in (2, 3, 4)])
    g = np.array([
        [np.log(all_markets[key].loc[treated, "fare"]) - np.log(all_markets[key].loc[control, "fare"])
         for key in pre_keys]
        for treated, control in group
    ])
    slopes = (np.linalg.pinv(x) @ g.T)[1, :]
    output["all_itinerary_pretrend_annualized"][name] = summary(4 * slopes)
    if name == "main":
        loo = [100*np.expm1(np.delete(direct, i).mean()) for i in range(len(direct))]
        output["main_leave_one_out_percent"] = {
            "min": float(np.min(loo)), "max": float(np.max(loo)),
            "min_removed_route": group[int(np.argmin(loo))][0],
            "max_removed_route": group[int(np.argmax(loo))][0],
            "median_pair_percent": float(100*np.expm1(np.median(direct))),
        }
        pd.DataFrame({"overlap_route": [t for t,c in group],
                      "control_route": [c for t,c in group],
                      "pair_log_change": direct,
                      "pair_percent_change": 100*np.expm1(direct),
                      "estimate_without_pair": loo}).to_csv(OUT / "route_influence.csv", index=False)

output["interpretation"] = (
    "All-itinerary fares include nonstop and connecting tickets on the same airport pair. "
    "The route influence and nonstop-share checks are descriptive; they do not repair control-group identification."
)
primary = json.loads((OUT / "results.json").read_text())
for name in pairs:
    delta = abs(output["direct_fare_replication"][name]["estimate"] - primary[name]["2015"]["percent"])
    if delta > 1e-9:
        raise AssertionError(f"Direct-fare replication differs for {name}: {delta}")
(OUT / "robustness.json").write_text(json.dumps(output, indent=2))
print(json.dumps(output, indent=2))

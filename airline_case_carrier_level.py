"""A carrier-level outcome that cannot move through carrier mix.

The route-average outcome used in ``airline_case_quarterly.py`` is an index over
whichever carriers happen to be selling tickets, so it responds to the
disappearance of AirTran whether or not any carrier changed a fare. This script
replaces the outcome and the control group at the same time:

  outcome   Southwest's own passenger-weighted market fare on the route.
  treated   Routes where Southwest and AirTran both had material 2009 Q2 traffic.
  control   Routes where Southwest and at least one carrier other than AirTran
            had material 2009 Q2 traffic, and AirTran sold no tickets at all.

The control group requires a second material carrier because Southwest's routes
are otherwise overwhelmingly Southwest-dominated: across all AirTran-free
Southwest routes the median 2009 Q2 route HHI is 0.99 against 0.54 on the
overlap routes, so an unrestricted pool cannot be balanced on concentration at
all. Restricting controls to routes where Southwest already faced somebody
brings the median to 0.52 and makes the contrast the intended one: the rival
Southwest absorbed was AirTran rather than someone it kept competing with.

GEOGRAPHY IS THIS DESIGN'S WEAK POINT, and the script measures it rather than
arguing it away. 20 of the 23 overlap routes touch a Florida airport, but only
10 of the 137 control candidates do, because Southwest's competitive non-AirTran
routes are concentrated in the West. An unconstrained match therefore pairs
Florida leisure routes with Western ones (MCO-PIT with DEN-MDW, FLL-PIT with
SAN-SEA), and those regions did not move together: among control routes alone,
where no AirTran ever flew, Southwest's own fare rose about 4.5% on Florida
routes against about 21% elsewhere from baseline to 2015. That gap biases the
unconstrained contrast DOWNWARD, so the headline understates rather than
flatters.

Constraining on geography pushes the estimate to roughly +21% to +25%, but only
by reusing eight to eleven Florida control routes, which wrecks fare balance.
Neither version pins the magnitude down. The script reports all three so the
range is visible; the memo treats the magnitude as unidentified and the sign and
the passing time-series diagnostics as the findings.

Both groups are Southwest routes throughout, so network-wide Southwest pricing,
fuel, and demand shocks are differenced out, and the contrast asks the narrower
question a case team would actually ask: did Southwest price its own seats
differently where the merger removed a competitor than where it removed nobody?

This is still not a causal estimate. Southwest chose where AirTran overlapped it,
the control routes changed under the merger too, and the premerger trend is
reported here precisely because it has to be checked rather than assumed.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd

from data_paths import quarter_file

HERE = Path(__file__).resolve().parent
DATA = HERE / "db1b_aggregated"
OUT = HERE / "airline_case_quarterly_results"
QUARTERS = [(y, q) for y in range(2007, 2016) for q in range(1, 5)]
KEYS = [f"{y}Q{q}" for y, q in QUARTERS]
BASE = ["2009Q3", "2009Q4", "2010Q1", "2010Q2"]
PRE_EARLY = ["2007Q3", "2007Q4", "2008Q1", "2008Q2"]
PRE_LATE = ["2008Q3", "2008Q4", "2009Q1", "2009Q2"]
CARRIER = "WN"
RNG = np.random.default_rng(20260921)

cells, own, route_totals = {}, {}, {}
for year, quarter in QUARTERS:
    key = f"{year}Q{quarter}"
    d = pd.read_csv(quarter_file(DATA, year, quarter))
    cells[key] = d
    w = d[d.carrier == CARRIER].set_index("route")
    own[key] = pd.DataFrame({"fare": w.fare_x_pax / w.passengers, "passengers": w.passengers})
    g = d.groupby("route").agg(passengers=("passengers", "sum"), fare_x_pax=("fare_x_pax", "sum"),
                               distance_x_pax=("distance_x_pax", "sum"))
    g["fare"] = g.fare_x_pax / g.passengers
    g["distance"] = g.distance_x_pax / g.passengers
    share = d.passengers / d.groupby("route").passengers.transform("sum")
    g["hhi"] = d.assign(share=share).groupby("route").share.apply(lambda s: float(np.square(s).sum()))
    route_totals[key] = g

persistent = set.intersection(*(set(own[k].index) for k in KEYS))
base = cells["2009Q2"]
material = base[base.passengers >= 50].groupby("route").carrier.agg(set)
all_carriers = base.groupby("route").carrier.agg(set)

treated = sorted({r for r, s in material.items() if {"WN", "FL"} <= s} & persistent)
controls = sorted({r for r, s in material.items()
                   if "WN" in s and len(s) >= 2 and "FL" not in all_carriers[r]} & persistent)
if len(treated) < 15 or len(controls) < 50:
    raise ValueError(f"Thin pools: {len(treated)} treated, {len(controls)} controls")

FLORIDA = {"MCO", "FLL", "TPA", "PBI", "RSW", "JAX", "MIA", "SRQ", "DAB", "EYW", "PNS", "TLH"}


def florida(route):
    return bool(set(route.split("-")) & FLORIDA)


pool = treated + controls
t0 = route_totals["2009Q2"].loc[pool]
w0 = own["2009Q2"].loc[pool]
features = pd.DataFrame({
    "log_own_fare": np.log(w0.fare),
    "log_own_passengers": np.log(w0.passengers),
    "log_distance": np.log(t0.distance),
    "hhi": t0.hhi,
}, index=pool)
sd = features.std(ddof=0)
z = (features - features.mean()) / sd

def build_match(florida_exact):
    """One-to-one nearest-neighbour matching without replacement, 2.5 caliper."""
    edges = sorted((float(np.linalg.norm(z.loc[t].values - z.loc[c].values)), t, c)
                   for t in treated for c in controls
                   if not florida_exact or florida(t) == florida(c))
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
    tm = features.loc[[p[0] for p in pairs]]
    cm = features.loc[[p[1] for p in pairs]]
    bal = ((tm.mean() - cm.mean())
           / np.sqrt((tm.var(ddof=1) + cm.var(ddof=1)) / 2)).to_dict()
    return pairs, bal


matched, balance = build_match(florida_exact=False)
florida_matched, florida_balance = build_match(florida_exact=True)


def build_stratified():
    """Nearest control inside the same Florida/non-Florida stratum, with replacement.

    Matching without replacement is impossible here: 20 treated routes touch
    Florida and only 10 control candidates do. Reusing controls buys geographic
    comparability at the cost of fare balance and effective sample size.
    """
    pairs = []
    for t in treated:
        cand = [(float(np.linalg.norm(z.loc[t].values - z.loc[c].values)), c)
                for c in controls if florida(c) == florida(t)]
        if cand:
            distance, c = min(cand)
            pairs.append((t, c, distance))
    tm = features.loc[[p[0] for p in pairs]]
    cm = features.loc[[p[1] for p in pairs]]
    bal = ((tm.mean() - cm.mean())
           / np.sqrt((tm.var(ddof=1) + cm.var(ddof=1)) / 2)).to_dict()
    return pairs, bal


stratified_matched, stratified_balance = build_stratified()


def gaps(pairs):
    return np.array([[np.log(own[k].loc[t, "fare"]) - np.log(own[k].loc[c, "fare"])
                      for k in KEYS] for t, c, _ in pairs])


gap = gaps(matched)


def window(names, g=None):
    g = gap if g is None else g
    return g[:, [KEYS.index(n) for n in names]].mean(axis=1)


def summarize(values):
    values = np.asarray(values, dtype=float)
    draws = RNG.choice(values, size=(10000, len(values)), replace=True).mean(axis=1)
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return {"n_pairs": int(len(values)), "log_difference": float(values.mean()),
            "percent": float(100 * np.expm1(values.mean())),
            "ci_low_percent": float(100 * np.expm1(lo)),
            "ci_high_percent": float(100 * np.expm1(hi))}


baseline = window(BASE)
windows = {"early_pre": PRE_EARLY, "late_pre": PRE_LATE, "base": BASE,
           **{str(y): [f"{y}Q{q}" for q in range(1, 5)] for y in range(2011, 2016)}}
contrasts = {name: summarize(window(keys) - baseline) for name, keys in windows.items()}

pre_keys = [f"{y}Q{q}" for y, q in QUARTERS if (y, q) <= (2010, 2)]
pre = gap[:, [KEYS.index(k) for k in pre_keys]]
time = np.arange(len(pre_keys), dtype=float)
season = np.array([int(k[-1]) for k in pre_keys])
design = np.column_stack([np.ones(len(time)), time] + [(season == q).astype(float) for q in (2, 3, 4)])
pretrend = summarize(4 * (np.linalg.pinv(design) @ pre.T)[1, :])

rolling = []
for i, key in enumerate(KEYS):
    if i < 3:
        continue
    value = summarize(gap[:, i - 3:i + 1].mean(axis=1) - baseline)
    rolling.append({"period": key, "year": int(key[:4]), "quarter": int(key[-1]),
                    "carrier_level_percent": value["percent"],
                    "carrier_level_ci_low": value["ci_low_percent"],
                    "carrier_level_ci_high": value["ci_high_percent"]})

output = {
    "question": (f"Did {CARRIER} price its own seats differently on routes where the merger removed "
                 f"AirTran than on comparable {CARRIER} routes where AirTran never sold tickets?"),
    "outcome": f"{CARRIER} passenger-weighted market fare on the route; no other carrier enters the index",
    "treated_definition": "WN and FL each with at least 50 sampled passengers in 2009 Q2",
    "control_definition": ("WN and at least one non-FL carrier each with at least 50 sampled "
                           "passengers, and zero FL tickets, in 2009 Q2"),
    "persistence_rule": f"{CARRIER} fare observed in all {len(KEYS)} quarters",
    "pools": {"treated": len(treated), "controls": len(controls)},
    "pairs": len(matched),
    "balance_standardized_difference": balance,
    "contrasts": contrasts,
    "pretrend_annualized_percent": pretrend,
    "placebo_early_to_base": summarize(window(BASE) - window(PRE_EARLY)),
    "alternative_baseline_2015_vs_late_pre": summarize(
        window([f"2015Q{q}" for q in range(1, 5)]) - window(PRE_LATE)),
    "leave_one_route_out_percent": None,
    "overlap_definition_sensitivity": None,
    "geography": {
        "note": ("20 of 23 overlap routes touch a Florida airport against 10 of "
                 f"{len(controls)} control candidates, so an unconstrained match compares "
                 "Florida routes with Western ones."),
        "treated_touching_florida": sum(florida(t) for t in treated),
        "controls_touching_florida": sum(florida(c) for c in controls),
        "pairs_agreeing_on_florida": sum(florida(t) == florida(c) for t, c, _ in matched),
        "control_only_placebo_2015": None,
        "stratified_sensitivity": {
            "pairs": len(stratified_matched),
            "distinct_controls_used": len({c for _, c, _ in stratified_matched}),
            "balance_standardized_difference": stratified_balance,
            "2015": summarize(window([f"2015Q{q}" for q in range(1, 5)], gaps(stratified_matched))
                              - window(BASE, gaps(stratified_matched))),
        },
    },
    "florida_exact_sensitivity": {
        "pairs": len(florida_matched),
        "balance_standardized_difference": florida_balance,
        "2015": summarize(window([f"2015Q{q}" for q in range(1, 5)], gaps(florida_matched))
                          - window(BASE, gaps(florida_matched))),
    },
    "interpretation": (
        "This outcome cannot move through carrier mix, and both groups are Southwest routes, so "
        "network-wide Southwest shocks difference out. The time-series diagnostics pass: the "
        "premerger slope is flat and the early-period placebo is near zero. The MAGNITUDE is not "
        "identified. Handling the Florida/West imbalance differently moves the 2015 contrast from "
        "about +12% to about +21-25%, and every geographically constrained version leans on eight "
        "to eleven reused control routes with poor fare balance. Report the sign and the range, "
        "not a point estimate: overlap was not assigned at random, the control routes were also "
        "exposed to the merger, and Southwest's own ticket mix changed when it absorbed AirTran."),
}
# Geography placebo: among control routes only - where AirTran never flew - did
# Florida and non-Florida Southwest fares move together? If not, the
# unconstrained match is contaminated and the direction of the bias is knowable.
def own_change(route):
    return (np.mean([np.log(own[k].loc[route, "fare"]) for k in [f"2015Q{q}" for q in range(1, 5)]])
            - np.mean([np.log(own[k].loc[route, "fare"]) for k in BASE]))


fl_ctl = np.array([own_change(c) for c in controls if florida(c)])
nf_ctl = np.array([own_change(c) for c in controls if not florida(c)])
output["geography"]["control_only_placebo_2015"] = {
    "florida_controls": summarize(fl_ctl),
    "non_florida_controls": summarize(nf_ctl),
    "gap_percent": float(100 * np.expm1(fl_ctl.mean() - nf_ctl.mean())),
    "implication": ("Control-route fares diverged sharply by region with no merger involved. "
                    "Because treated routes are mostly Florida and matched controls mostly are "
                    "not, this biases the unconstrained contrast downward."),
}

# Robustness: influence of any single route, and of the overlap threshold.
post = window([f"2015Q{q}" for q in range(1, 5)])
effects = post - baseline
loo = [float(100 * np.expm1(np.delete(effects, i).mean())) for i in range(len(effects))]
output["leave_one_route_out_percent"] = {
    "min": min(loo), "max": max(loo),
    "min_removed_route": matched[int(np.argmin(loo))][0],
    "max_removed_route": matched[int(np.argmax(loo))][0],
}

base_quarter = cells["2009Q2"]


def minority_share(route):
    g = base_quarter[base_quarter.route == route]
    total = g.passengers.sum()
    return float(min(g.loc[g.carrier == "WN", "passengers"].sum(),
                     g.loc[g.carrier == "FL", "passengers"].sum()) / total)


shares = np.array([minority_share(t) for t, _, _ in matched])
output["overlap_definition_sensitivity"] = {
    f"minority_share_at_least_{th:.2f}": summarize(effects[shares >= th])
    for th in (0.00, 0.10, 0.20)
}

(OUT / "carrier_level.json").write_text(json.dumps(output, indent=2))
pd.DataFrame(matched, columns=["overlap_route", "wn_only_control", "match_distance"]).to_csv(
    OUT / "carrier_level_matched_routes.csv", index=False)
pd.DataFrame(rolling).to_csv(OUT / "carrier_level_path.csv", index=False)
print(json.dumps({"pools": output["pools"], "pairs": len(matched), "balance": balance,
                  "2015": contrasts["2015"], "2013": contrasts["2013"],
                  "late_pre": contrasts["late_pre"], "early_pre": contrasts["early_pre"],
                  "pretrend": pretrend}, indent=2))

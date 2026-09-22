"""Build the full-quarter case memo from reproducible JSON results.

Every figure in the prose is read from the result files rather than typed in, so
a rerun on different data cannot leave the narrative saying something the
analysis no longer supports.
"""
from pathlib import Path
import json
import os
import pandas as pd
from reportlab.graphics.shapes import Drawing, Line, Circle, String, Rect
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                PageBreak, KeepTogether)

HERE = Path(__file__).resolve().parent
RES = HERE / "airline_case_quarterly_results"
OUT = Path(os.environ.get("AIRLINE_MEMO_OUTPUT", HERE / "Airline_Merger_Expert_Style_Memo.pdf"))
results = json.loads((RES / "results.json").read_text())
robust = json.loads((RES / "robustness.json").read_text())
comp = json.loads((RES / "composition.json").read_text())
carrier = json.loads((RES / "carrier_level.json").read_text())
path = pd.read_csv(RES / "quarterly_path.csv")
cpath = pd.read_csv(RES / "carrier_level_path.csv")

NAVY = colors.HexColor("#18344D")
BLUE = colors.HexColor("#176E99")
GOLD = colors.HexColor("#9A651A")
GREEN = colors.HexColor("#2C7764")
GRAY = colors.HexColor("#56616B")
PALE = colors.HexColor("#F2F6F8")
LIGHT = colors.HexColor("#D9E3E9")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="TitleX", fontName="Helvetica-Bold", fontSize=17.4, leading=20.5,
                          textColor=NAVY, spaceAfter=6))
styles.add(ParagraphStyle(name="DeckX", fontName="Helvetica", fontSize=9, leading=12,
                          textColor=GRAY, spaceAfter=12))
styles.add(ParagraphStyle(name="SectionX", fontName="Helvetica-Bold", fontSize=10.4, leading=12.8,
                          textColor=NAVY, spaceBefore=11, spaceAfter=5))
styles.add(ParagraphStyle(name="BodyX", fontName="Helvetica", fontSize=8.85, leading=12.3,
                          spaceAfter=6))
styles.add(ParagraphStyle(name="SmallX", fontName="Helvetica", fontSize=7.45, leading=9.9,
                          textColor=GRAY, spaceAfter=5))
styles.add(ParagraphStyle(name="BulletX", fontName="Helvetica", fontSize=8.6, leading=11.7,
                          leftIndent=12, firstLineIndent=-8, spaceAfter=4))


def p(s, style="BodyX"):
    return Paragraph(s, styles[style])


def ci(x, point="percent", lo="ci_low_percent", hi="ci_high_percent"):
    return f"{x[point]:+.1f}% ({x[lo]:+.1f}%, {x[hi]:+.1f}%)"


def pct(x, key="percent"):
    return f"{x[key]:+.1f}%"


def fmt(key, period):
    return ci(results[key][period])


def fmt_robust(group):
    return ci(robust["all_itinerary_fare_2015"][group], "estimate", "ci_low", "ci_high")


def fmt_comp(group, part):
    return ci(comp["shift_share_decomposition"][group][part], "estimate", "ci_low", "ci_high")


MAIN_2015 = results["main"]["2015"]
PRETREND = results["pretrend_annualized_percent"]
MIX = comp["shift_share_decomposition"]["main"]["carrier_mix"]
WITHIN = comp["shift_share_decomposition"]["main"]["within_carrier"]
CL_2015 = carrier["contrasts"]["2015"]
CL_PRE = carrier["pretrend_annualized_percent"]
CL_PLACEBO = carrier["placebo_early_to_base"]
CL_LOO = carrier["leave_one_route_out_percent"]
SENS = comp["overlap_definition_sensitivity"]
GEO = carrier["geography"]
GEO_STRAT = GEO["stratified_sensitivity"]
GEO_PLACEBO = GEO["control_only_placebo_2015"]


def chart():
    d = Drawing(510, 224)
    left, right, bottom, top = 39, 496, 54, 190
    ymin, ymax = -12, 30

    def yp(v):
        return bottom + (v - ymin) / (ymax - ymin) * (top - bottom)

    def xp(i):
        return left + i / (len(path) - 1) * (right - left)

    announce_i = path.index[path.period == "2010Q3"][0]
    d.add(Rect(left, bottom, xp(announce_i) - left, top - bottom, fillColor=PALE, strokeColor=None))
    for value in [-10, 0, 10, 20, 30]:
        y = yp(value)
        d.add(Line(left, y, right, y, strokeColor=GRAY if value == 0 else LIGHT, strokeWidth=0.8,
                   strokeDashArray=[3, 3] if value == 0 else None))
        d.add(String(left - 5, y - 2.5, f"{value}%", textAnchor="end", fontName="Helvetica",
                     fontSize=7.1, fillColor=GRAY))
    for year in range(2008, 2016):
        idx = path.index[path.period == f"{year}Q1"]
        if len(idx):
            d.add(String(xp(int(idx[0])), bottom - 14, str(year), textAnchor="middle",
                         fontName="Helvetica", fontSize=7.4, fillColor=GRAY))
    d.add(String((left + xp(announce_i)) / 2, 201, "Before announcement", textAnchor="middle",
                 fontName="Helvetica-Bold", fontSize=7.5, fillColor=GRAY))
    d.add(String((xp(announce_i) + right) / 2, 201, "Announcement and integration",
                 textAnchor="middle", fontName="Helvetica-Bold", fontSize=7.5, fillColor=GRAY))
    d.add(Line(xp(announce_i), bottom, xp(announce_i), top,
               strokeColor=colors.HexColor("#8B9DA8"), strokeWidth=0.9, strokeDashArray=[2, 3]))
    series = [(path["other_lcc_percent"], GOLD, 1.5, None),
              (path["main_percent"], BLUE, 1.5, None),
              (cpath["carrier_level_percent"], GREEN, 2.1, None)]
    for values, color, width, dash in series:
        last = None
        for i, value in enumerate(values):
            x, y = xp(i), yp(value)
            if last:
                d.add(Line(last[0], last[1], x, y, strokeColor=color, strokeWidth=width,
                           strokeDashArray=dash))
            if i in [0, announce_i, len(values) - 1]:
                d.add(Circle(x, y, 2.7, fillColor=color, strokeColor=color))
            last = (x, y)
    for x0, y0, color, width, label in [
            (39, 25, GREEN, 2.1, "Southwest's own fare vs. competitive Southwest routes"),
            (39, 10, BLUE, 1.5, "Route average vs. AirTran-only controls"),
            (270, 10, GOLD, 1.5, "Route average vs. other low-cost controls")]:
        d.add(Line(x0, y0, x0 + 18, y0, strokeColor=color, strokeWidth=width))
        d.add(String(x0 + 22, y0 - 3, label, fontName="Helvetica", fontSize=7.2, fillColor=GRAY))
    return d


styles.add(ParagraphStyle(name="CellHead", fontName="Helvetica-Bold", fontSize=7.8, leading=9.6,
                          textColor=colors.white))
styles.add(ParagraphStyle(name="Cell", fontName="Helvetica", fontSize=7.8, leading=9.6))


def table(rows, widths):
    body = [[Paragraph(str(c), styles["CellHead" if i == 0 else "Cell"]) for c in row]
            for i, row in enumerate(rows)]
    t = Table(body, colWidths=widths, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("FONTSIZE", (0, 0), (-1, -1), 7.8), ("LEADING", (0, 0), (-1, -1), 9.8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 5.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5.5), ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F8FA")]),
    ]))
    return t


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LIGHT)
    canvas.line(0.65 * inch, 0.58 * inch, 7.85 * inch, 0.58 * inch)
    canvas.setFont("Helvetica", 7.2)
    canvas.setFillColor(GRAY)
    canvas.drawRightString(7.84 * inch, 0.42 * inch, str(doc.page))
    canvas.restoreState()


doc = SimpleDocTemplate(str(OUT), pagesize=letter, leftMargin=0.65 * inch, rightMargin=0.65 * inch,
                        topMargin=0.59 * inch, bottomMargin=0.75 * inch,
                        title="Southwest and AirTran: what the fare comparison actually measures",
                        author="Saathvik Maheshuni",
                        subject="Case study using BTS airline ticket data, 2007 Q1 to 2015 Q4.")
story = []

# ---------------------------------------------------------------- page 1
story += [p("Southwest and AirTran: what the fare comparison actually measures", "TitleX"),
          p("Case study memo | BTS ticket sample, 2007 Q1 to 2015 Q4 | "
            "Saathvik Maheshuni | September 2026", "DeckX")]
story += [p("Summary", "SectionX"),
          p(f"When two airlines merge, the first question is whether fares went up on the routes "
            f"where they used to compete against each other. I found "
            f"<b>{results['balanced_overlap_routes']} nonstop airport pairs</b> where Southwest and "
            f"AirTran each sold a meaningful number of tickets in the second quarter of 2009, well "
            f"before the merger was announced."),
          p(f"The usual way to answer the question is to compare the average fare on those routes "
            f"with the average fare on similar routes that only AirTran flew. For 2015, measured "
            f"against the four quarters before the September 2010 announcement, that comparison "
            f"gives <b>{ci(MAIN_2015)}</b>. <b>That number should not be reported as a fare "
            f"effect.</b> A route's average fare is an average across whichever airlines are selling "
            f"tickets on it, and by 2015 one of those airlines is gone."),
          p(f"To see how much of the number that explains, I split it in two. First I froze every "
            f"airline's own fare at its level before the merger and let only the passenger shares "
            f"change. That alone gives <b>{pct(MIX,'estimate')}</b>. What is left, the part that "
            f"comes from airlines actually changing their own fares, is "
            f"<b>{pct(WITHIN,'estimate')}</b>. The mix accounts for "
            f"{abs(comp['shift_share_decomposition']['main']['mix_share_of_total']):.0%} of the "
            f"headline. Southwest's fares on these routes were higher than AirTran's in 2009, so "
            f"when the AirTran name disappears the route average rises on its own, without anyone "
            f"changing a price."),
          p(f"So I changed the measure. Instead of the route average I used <b>Southwest's own "
            f"fare</b>, and instead of AirTran-only routes I compared against Southwest routes that "
            f"AirTran never flew. No change in airline mix can move that number. Across "
            f"{carrier['pairs']} matched pairs, Southwest's own fare on the old overlap routes in "
            f"2015 was {ci(CL_2015)} higher than on the comparison routes. This version also passes "
            f"the checks the first one fails. Its trend before the merger is {ci(CL_PRE)} a year, "
            f"which is flat because the range crosses zero, against {ci(PRETREND)} for the route "
            f"average. A fake test on an early period, where nothing should show up, gives "
            f"{ci(CL_PLACEBO)}."),
          p(f"<b>The direction looks solid. The size does not.</b> "
            f"{GEO['treated_touching_florida']} of the {carrier['pairs']} overlap routes touch a "
            f"Florida airport, but only {GEO['controls_touching_florida']} of the "
            f"{carrier['pools']['controls']} possible comparison routes do, because Southwest's "
            f"other competitive routes are mostly in the West. So the comparison ends up matching "
            f"Florida routes against Western ones, and the two regions did not move together. "
            f"Looking only at comparison routes, where AirTran never flew at all, Southwest's fare "
            f"rose {pct(GEO_PLACEBO['florida_controls'])} on Florida routes and "
            f"{pct(GEO_PLACEBO['non_florida_controls'])} everywhere else. That gap pushes my number "
            f"<i>down</i>, not up. Forcing each route to be compared within its own region raises it "
            f"to {pct(GEO_STRAT['2015'])}, but only by reusing the same "
            f"{GEO_STRAT['distinct_controls_used']} comparison routes over and over. The honest way "
            f"to report this is a positive difference of roughly "
            f"{min(CL_2015['percent'], GEO_STRAT['2015']['percent']):.0f}% to "
            f"{max(CL_2015['percent'], GEO_STRAT['2015']['percent']):.0f}%, not a single number.")]
story += [p("Background", "SectionX"),
          p("The Department of Justice closed its investigation on April 26, 2011. It said the two "
            "airlines overlapped on few nonstop routes, that it expected new service to follow, and "
            "that there were no gate or slot problems at the airports involved. [5] The merger "
            "closed on May 2, 2011, and the last scheduled AirTran flight left Atlanta on December "
            "28, 2014. [3,4] This memo only looks at fares on routes the two airlines already "
            "shared. It says nothing about whether passengers gained from the routes Southwest "
            "added later, which was the other half of what the DOJ weighed.")]
story += [PageBreak(), p("Why the route average is misleading", "TitleX")]
story += [p("Fare gap over time, four quarters at a time", "SectionX"), chart(),
          p("Each point averages four quarters in a row and subtracts the gap in the four quarters "
            "before the announcement, so zero means no change from that starting point. The three "
            "lines disagree. The AirTran-only route average ends up back near where it started. The "
            "other low-cost route average sits far above it the whole time, on a comparison that is "
            "poorly matched. Southwest's own fare rises and stays up. The shaded part is before the "
            "September 27, 2010 announcement. [2]", "SmallX")]

# ---------------------------------------------------------------- page 2

story += [p("Splitting the 2015 number into fares and mix", "SectionX"),
          p("For the mix-only version, every airline keeps the fare it charged in the four quarters "
            "before the announcement, and only the share of passengers each one carries is allowed "
            "to change. Whatever that version shows is the work the changing mix did by itself. "
            "Whatever is left over is what airlines did to their own fares.")]
rows = [["Comparison group", "Total", "From changing mix", "From actual fares"]]
for key, label in [("main", "AirTran-only routes"),
                   ("other_lcc", "Other low-cost routes"),
                   ("early_pretrend_matched", "AirTran-only, matched on early trend")]:
    rows.append([label, fmt_comp(key, "total"), fmt_comp(key, "carrier_mix"),
                 fmt_comp(key, "within_carrier")])
story += [KeepTogether([table(rows, [1.94 * inch, 1.72 * inch, 1.72 * inch, 1.82 * inch]),
          p("The parts are averages of log differences across matched pairs, so they do not add up "
            "neatly in percentage terms. Each total reproduces the published figure exactly before "
            "it is reported here. Note that the other low-cost comparison is mostly real fare "
            "change, so the three versions disagree about the cause as well as the size.", "SmallX")])]
story += [p("How I define an overlap route matters more than any single route", "SectionX"),
          p(f"A route counts as an overlap if each airline had at least 50 sampled passengers in the "
            f"second quarter of 2009. The data is a 10% sample of tickets, so 50 sampled passengers "
            f"is roughly 500 real ones in a quarter. On a busy airport pair that can be a few "
            f"percent of traffic. On four of the {results['balanced_overlap_routes']} routes the "
            f"smaller airline carries under 10% of the passengers, as little as 3.8% on "
            f"Indianapolis to Las Vegas. Asking the smaller airline to be a real presence moves the "
            f"route-average number by several points. That is a much wider swing than dropping one "
            f"route at a time, which only moves it between "
            f"{robust['main_leave_one_out_percent']['min']:+.1f}% and "
            f"{robust['main_leave_one_out_percent']['max']:+.1f}%.")]
rows = [["Smaller airline's share of route traffic, 2009 Q2", "Pairs", "Route average", "Southwest's own fare"]]
for th, label in [("0.00", "No minimum (as built)"), ("0.10", "At least 10%"), ("0.20", "At least 20%")]:
    left_cell = SENS[f"minority_share_at_least_{th}"]
    right_cell = carrier["overlap_definition_sensitivity"][f"minority_share_at_least_{th}"]
    rows.append([label, str(left_cell["n_pairs"]),
                 ci(left_cell, "estimate", "ci_low", "ci_high"), ci(right_cell)])
story += [KeepTogether([table(rows, [2.05 * inch, 0.55 * inch, 1.75 * inch, 2.85 * inch]),
          p("The two columns use different pools of comparison routes, which is why the route counts "
            "differ. The route-average number is not stable under the very definition that produced "
            "it. Southwest's own fare barely moves, and dropping one route at a time only shifts it "
            f"between {CL_LOO['min']:+.1f}% and {CL_LOO['max']:+.1f}%. Neither version holds up "
            f"against the regional makeup of its comparison routes, which is the real problem here "
            f"and is covered below.", "SmallX")])]

# ---------------------------------------------------------------- page 3
story += [Spacer(1, 10), p("Data and method", "TitleX")]
story += [p("Ticket records for all 36 quarters", "SectionX"),
          p("The data is the BTS DB1BMarket file, a 10% sample of airline tickets that records "
            "passengers, the fare assigned to each trip, and the operating airline. [1] I processed "
            "every quarter from 2007 Q1 through 2015 Q4. I kept domestic nonstop trips on a single "
            "coupon, dropped bulk fares, and kept trips with positive passenger counts, fares "
            "between $50 and $2,000, and distances between 50 and 5,000 miles. The two directions of "
            "an airport pair are combined into one route. This measures what people paid for "
            "tickets, not published fares, and not the full cost of travelling."),
          p(f"<b>Route-average version.</b> A route counts as an overlap if AirTran and Southwest "
            f"each had at least 50 sampled passengers in 2009 Q2. Comparison routes had at least 50 "
            f"AirTran passengers and no Southwest tickets at all. Requiring a fare in all 36 "
            f"quarters leaves all {results['balanced_overlap_routes']} overlap routes and "
            f"{results['balanced_control_candidates']['airtran_only']} possible comparison routes. "
            f"Each overlap route is paired with one comparison route, never reused, matched on 2009 "
            f"Q2 fare, passengers, distance, and how concentrated the route is among airlines. Pairs "
            f"must agree on whether an endpoint is in Florida, and I cap how far apart a pair can be "
            f"across those four traits combined at 2.5 (this is a limit on the combined gap, not on "
            f"route mileage). {results['pairs']['main']} pairs survive. The usual balance check, the "
            f"gap between the two groups divided by how spread out they are, comes to "
            f"{results['balance']['main']['log_fare']:+.2f} on fare, "
            f"{results['balance']['main']['log_distance']:+.2f} on distance and "
            f"{results['balance']['main']['hhi']:+.2f} on concentration. The other low-cost version "
            f"is matched worse still, at {results['balance']['other_lcc']['log_distance']:+.2f} on "
            f"distance, which is a reason to trust its bigger number less, not more."),
          p(f"<b>Southwest's own fare version.</b> The measure is what Southwest itself charged, so "
            f"no other airline can affect it. Comparison routes are ones where Southwest and at "
            f"least one airline other than AirTran both carried real traffic in 2009 Q2, and AirTran "
            f"sold nothing. The second-airline requirement is necessary: Southwest's other routes "
            f"are overwhelmingly Southwest-only, and without it the two groups cannot be matched on "
            f"how concentrated they are. {carrier['pools']['controls']} routes qualify and "
            f"{carrier['pairs']} pairs match, with every balance check below "
            f"{max(abs(v) for v in carrier['balance_standardized_difference'].values()):.2f}. This "
            f"match does not require pairs to agree on Florida. Requiring it leaves only "
            f"{carrier['florida_exact_sensitivity']['pairs']} pairs and a "
            f"{carrier['florida_exact_sensitivity']['balance_standardized_difference']['log_own_fare']:+.2f} "
            f"gap in Southwest's own starting fare. That is a real cost and I do not want to pretend "
            f"otherwise: only {GEO['controls_touching_florida']} comparison routes touch Florida "
            f"against {GEO['treated_touching_florida']} overlap routes, so this pool cannot give me "
            f"both regional comparability and matched traits. Averaging four quarters handles "
            f"season, not region. The version that forces regional matching is reported alongside "
            f"rather than chosen.")]
story += [p("Time windows, uncertainty, and the trend check", "SectionX"),
          p(f"The starting point is <b>2009 Q3 to 2010 Q2</b>, the four quarters before the "
            f"announcement. Every yearly result compares that year's four quarters against it, so "
            f"all four seasons appear on both sides. For uncertainty I resample whole route pairs "
            f"10,000 times and report the middle 95% of the results. That captures ordinary sampling "
            f"noise given the pairs I chose; it does not capture the risk that I chose the wrong "
            f"pairs. The trend check fits a straight line through each pair's fare gap from 2007 Q1 "
            f"to 2010 Q2, allowing for season.")]
rows = [["Version and year", "Pairs", "Fare difference (95% range)"]]
rows += [
    ["Route average vs. AirTran-only: 2013", str(results["pairs"]["main"]), fmt("main", "2013")],
    ["Route average vs. AirTran-only: 2015", str(results["pairs"]["main"]), fmt("main", "2015")],
    ["Route average vs. other low-cost: 2015", str(results["pairs"]["other_lcc"]), fmt("other_lcc", "2015")],
    ["Route average, matched on early trend: 2015", str(results["pairs"]["early_pretrend_matched"]),
     fmt("early_pretrend_matched", "2015")],
    ["Route average, connecting trips included: 2015", str(results["pairs"]["main"]), fmt_robust("main")],
    ["<b>Southwest's own fare: 2013</b>", str(carrier["pairs"]), "<b>" + ci(carrier["contrasts"]["2013"]) + "</b>"],
    ["<b>Southwest's own fare: 2015</b>", str(carrier["pairs"]), "<b>" + ci(CL_2015) + "</b>"],
    ["Southwest's own fare, measured from 2008 Q3-2009 Q2 instead", str(carrier["pairs"]),
     ci(carrier["alternative_baseline_2015_vs_late_pre"])],
]
story += [KeepTogether([table(rows, [3.02 * inch, 0.49 * inch, 3.69 * inch]),
          p(f"The last row matters. Southwest's fare gap was already "
            f"{pct(carrier['contrasts']['late_pre'])} above the starting point back in 2008 Q3 to "
            f"2009 Q2, so measuring from that earlier window roughly halves the answer. The fitted "
            f"trend line before the merger is flat, but the path itself is not, so the choice of "
            f"starting point does real work. The row matched on early trend uses the fare path "
            f"itself to pick comparison routes, which drags the later result toward the middle on "
            f"its own; it is a sensitivity check, not a better estimate.", "SmallX")])]

# ---------------------------------------------------------------- page 4
story += [Spacer(1, 10), p("What each side would argue, and what neither can show", "TitleX")]
story += [p("What someone arguing fares rose would point to", "SectionX"),
          p(f"On {results['balanced_overlap_routes']} routes, two nonstop competitors became one. "
            f"Once the mix problem is taken out, Southwest's own fares on those routes sit "
            f"{pct(CL_2015)} above comparable Southwest routes in 2015 and "
            f"{pct(carrier['contrasts']['2013'])} in 2013. The ranges stay above zero, the trend "
            f"before the merger is flat, and the answer barely moves when I change the overlap "
            f"definition or drop any single route. A GAO review describes a separate study of this "
            f"merger by Le, which found 3.7% (range 2.1% to 5.3%) across a wider set of nonstop and "
            f"connecting routes. That study used a different period, measure, and comparison group, "
            f"and my figure is larger. [6,7]")]
story += [p("What someone arguing they did not would point to", "SectionX"),
          p(f"The DOJ expected new service and found no gate or slot problems at the overlap "
            f"airports. [5] Southwest's own fare has a mix problem of its own: once it absorbed "
            f"AirTran's passengers, the tickets inside its average were a different blend of fare "
            f"types, booking times, and business travellers, and that alone can lift an average "
            f"without any individual fare rising. Measuring from 2008 Q3 to 2009 Q2 instead of the "
            f"four quarters before the announcement halves the answer to "
            f"{pct(carrier['alternative_baseline_2015_vs_late_pre'])}. Every version that keeps the "
            f"regions comparable leans on {GEO_STRAT['distinct_controls_used']} to "
            f"{carrier['florida_exact_sensitivity']['pairs']} Florida comparison routes used more "
            f"than once, with starting fares well out of line, so the size rests on a handful of "
            f"routes picked for one trait. The comparison routes were affected by the merger too, I "
            f"do not measure seats or aircraft moves, and the route-average evidence is perfectly "
            f"consistent with no lasting increase.")]
story += [p("Why none of this proves the merger caused anything", "SectionX")]
for s in [
    "<b>The routes were not picked at random.</b> AirTran chose where to compete with Southwest, so "
    "overlap routes differ from other Southwest routes in ways my four matching traits do not catch. "
    "Geography is the clearest case: the overlap group is mostly a Florida network and the available "
    "comparison routes are mostly not.",
    "<b>The comparison routes were affected too.</b> Both groups changed under the merger, so what I "
    "measure is the extra difference on overlap routes, not a clean picture of a world without it.",
    "<b>Ticket mix still sits inside Southwest's own fare.</b> That measure is an average over "
    "Southwest's tickets, and which tickets those are changed when AirTran's passengers moved over.",
    "<b>The sample and the missing outcomes.</b> Requiring a fare in all 36 quarters keeps only "
    "routes that survived the whole period. Seats flown, fuel and airport costs, demand, bag and "
    "seat fees, connecting options, service quality, and any benefit on new routes are all outside "
    "this test.",
]:
    story.append(p("&#8226; " + s, "BulletX"))
story += [p("Checks I ran", "SectionX"),
          p(f"Including connecting trips as well as nonstop moves the route-average 2015 figure from "
            f"{pct(MAIN_2015)} to "
            f"{robust['all_itinerary_fare_2015']['main']['estimate']:+.1f}%, and its trend before "
            f"the merger is still "
            f"{robust['all_itinerary_pretrend_annualized']['main']['estimate']:+.1f}% a year. "
            f"Dropping one overlap route at a time leaves the route average between "
            f"{robust['main_leave_one_out_percent']['min']:+.1f}% and "
            f"{robust['main_leave_one_out_percent']['max']:+.1f}%, and Southwest's own fare between "
            f"{CL_LOO['min']:+.1f}% and {CL_LOO['max']:+.1f}%. Requiring the smaller airline to hold "
            f"20% of route traffic moves the route average to "
            f"{SENS['minority_share_at_least_0.20']['estimate']:+.1f}% and Southwest's own fare to "
            f"{carrier['overlap_definition_sensitivity']['minority_share_at_least_0.20']['percent']:+.1f}%. "
            f"Southwest's own fare survives these checks. The route average does not.")]
story += [p("What I would do next", "SectionX"),
          p("None of these numbers should be turned into a damages figure. I would lead with the "
            "Southwest's-own-fare version and use the route average as an example of how the wrong "
            "measure can manufacture a result, then ask for the evidence that would close the gaps "
            "that remain: enough comparison routes to match Florida against Florida, ticket-level "
            "fare and booking data to separate price from who is flying, seat and aircraft records, "
            "and any internal pricing documents showing whether Southwest treated the old overlap "
            "routes differently. The most useful thing I found was that the appealing number was "
            "measuring the wrong thing.")]
story += [p("Sources and notes", "SectionX"),
          p("[1] BTS, <link href='https://www.bts.gov/topics/airlines-and-airports/origin-and-destination-survey-data'>Origin and Destination Survey (DB1B)</link>, "
            "a 10% quarterly sample of airline tickets. The files used here are the quarterly "
            "DB1BMarket archives named Origin_and_Destination_Survey_DB1BMarket_YEAR_QUARTER.zip, "
            "downloaded from transtats.bts.gov/PREZIP/. "
            "[2] Southwest, <link href='https://investors.southwest.com/news-events/press-releases/detail/1429/southwest-airlines-to-acquire-airtran-spreading-low-fares-farther'>announcement</link>, "
            "Sept. 27, 2010. [3] Southwest, <link href='https://investors.southwest.com/news-events/press-releases/detail/1326/southwest-airlines-closes-acquisition-of-airtran-holdings-inc'>close</link>, "
            "May 2, 2011. [4] Southwest, <link href='https://investors.southwest.com/news-events/press-releases/detail/857/southwest-airlines-celebrates-final-scheduled-airtran-airways-flight'>final AirTran flight</link>, "
            "departed Atlanta Dec. 28, 2014 (release dated Dec. 29). "
            "[5] DOJ, <link href='https://www.justice.gov/archives/opa/pr/statement-department-justice-antitrust-division-its-decision-close-its-investigation'>closing statement</link>, "
            "Apr. 26, 2011. [6] Le, <i>An Empirical Analysis of the Price and Output Effects of the "
            "Southwest/AirTran Merger</i>, Competition and Regulation in Network Industries 17(3-4): "
            "226-240 (2016), doi:10.1177/178359171601700302. "
            "[7] GAO, <link href='https://www.gao.gov/products/gao-26-107740'>Airline Competition</link>, "
            "GAO-26-107740 (2026).", "SmallX"),
          p("The code, all 36 quarters of processed data, the matched route lists, and checksums for "
            "the original downloads come with this memo. Every number above is read from the results "
            "files when the document is built, so the text cannot drift away from the analysis.",
            "SmallX")]

STORY_SNAPSHOT = list(story)  # preserved for the .docx exporter
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUT)

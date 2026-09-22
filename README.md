# Southwest-AirTran: full quarterly antitrust case study

This is a case study on the Southwest–AirTran merger. It asks whether fares changed on the airport pairs where both airlines used to fly, compared with similar routes. It is a portfolio exercise, **not** an estimate of what the merger caused, an expert opinion, or a damages calculation.

**The main thing I found is about measurement, not about airlines.** The obvious number to look at is the average fare on a route. But that average is taken across whichever airlines are selling tickets, and the merger takes one of them away, so the average moves even when nobody changes a price. Splitting the number apart shows that this accounts for more than the whole result. Switching to Southwest's own fare, and comparing against Southwest routes AirTran never flew, removes the problem and gives a version that passes the trend checks the first one fails. Even that version is descriptive only: the routes were not picked at random, the comparison routes were affected by the merger too, and Southwest's own mix of passengers changed when it absorbed AirTran's.

## Results at a glance

2015 compared with the four quarters before the September 2010 announcement, across 24 confirmed nonstop overlap routes, using 36 quarters of BTS ticket data.

| | Route average | Southwest's own fare |
|---|---|---|
| 2015 difference | +1.3% (-4.9%, +8.1%) | +12.0% (+6.7%, +17.9%) |
| Part from changing airline mix | +2.0% of a +1.3% total | cannot happen by design |
| Trend before the merger | +2.9% (+0.2%, +5.4%) per year — **fails** | +1.4% (-1.4%, +4.5%) per year — passes |
| Fake test on an early period | +4.4% | -1.0% (-6.7%, +5.5%) |
| Worst balance check | 0.31 | 0.24 |
| Dropping one route at a time | -0.3% to +2.8% | +10.8% to +13.0% |
| Overlap rule, none to 20% | +1.3% to +9.6% | +12.0% to +12.0% |

The size of the Southwest's-own-fare figure is **not pinned down**: 20 of 23 overlap routes touch a Florida airport against 10 of 137 comparison candidates, and among comparison routes alone Southwest's fare rose +4.5% on Florida routes against +20.8% elsewhere. Forcing regional matching raises the figure to +21.2% while reusing 8 comparison routes. Report the direction and the range, not a single number.

## Files

- `Airline_Merger_Expert_Style_Memo.pdf` and `.docx`: the memo, with the fare path over time, what each side would argue, and the limits. Both are rebuilt by the scripts below, so they always match the numbers in the results files.
- `process_db1b.py`: turns each BTS download into totals by airline, route, and quarter.
- `process_db1b_all_itineraries.py`: does the same but keeps connecting trips separate, as a check on how fares are measured.
- `airline_case_quarterly.py`: loads all 36 quarters, sorts routes into groups, matches comparison routes, checks the trend before the merger, and writes the results.
- `airline_case_robustness.py`: adds connecting trips, tracks the nonstop share, and tests what happens when one route is dropped. It also rebuilds the main numbers on its own as a check.
- `airline_case_composition.py`: splits the route-average number into the part caused by which airline is selling tickets and the part caused by real fare changes, then re-runs it as the overlap rule tightens. It checks its own totals against the published figures first.
- `airline_case_carrier_level.py`: the second version — Southwest's own fare on overlap routes against matched Southwest routes AirTran never flew — with its own matching, balance, trend, fake-period, drop-one-route, and threshold checks.
- `build_airline_case_quarterly_pdf.py`: builds the PDF. Every number in the text is read from the results files when the document is built, not typed in, so rerunning on new data cannot leave the text saying something the analysis no longer supports.
- `export_memo_content.py` and `build_airline_case_quarterly_docx.js`: build the Word version. The first writes out the same content the PDF uses, plus the chart as an image; the second turns it into a `.docx`. Both documents come from one source, so they cannot drift apart.
- `db1b_aggregated/`: the 36 processed files, one per quarter, gzipped. The raw ticket records are not included because the downloads run to several gigabytes.
- `db1b_all_itineraries/`: 36 gzipped files covering both nonstop and connecting trips.
- `airline_case_quarterly_results/`: all the numbers, the quarter-by-quarter path, the period comparisons, and the lists of matched routes.
- `AUDIT.md`: what reproduced, what was wrong, what changed, and what is still breakable. Worth reading before the results.
- `data_paths.py`: finds a processed quarter whether it is stored gzipped or plain.
- `raw_file_sha256.txt`: checksums for all 36 original downloads, so anyone can confirm they have the same files.


## Data provenance and reproduction

The source is the U.S. Bureau of Transportation Statistics (BTS), Airline Origin and Destination Survey DB1BMarket. The 2007 Q1-2015 Q4 files were downloaded from this official pattern:

`https://transtats.bts.gov/PREZIP/Origin_and_Destination_Survey_DB1BMarket_YEAR_QUARTER.zip`

Replace `YEAR` with 2007 through 2015 and `QUARTER` with 1 through 4. BTS describes DB1B as a 10% quarterly sample of airline tickets: <https://www.bts.gov/topics/airlines-and-airports/origin-and-destination-survey-data>. The DB1BMarket table gives directional market fares, passengers, and the operating airline.

Python 3 requires `pandas`, `numpy`, and `reportlab` (tested versions in `requirements.txt`).

To reproduce every number in the memo from the data already in this repository:

```
git clone https://github.com/Saathvik007/southwest-airtran-merger-retrospective.git
cd southwest-airtran-merger-retrospective
pip install -r requirements.txt
python airline_case_quarterly.py
python airline_case_robustness.py
python airline_case_composition.py
python airline_case_carrier_level.py
```

Each script rewrites its own files in `airline_case_quarterly_results/`; `git status` should report no changes, because the committed results are exactly what these scripts produce. Two of the scripts also check themselves: the robustness script rebuilds the main estimates independently and asserts they match, and the composition script asserts its decomposition totals reproduce the published contrasts before it reports anything.

Step by step, including rebuilding the documents and recreating the processed data from the raw BTS downloads:

1. The included processed data suffice to rerun the analysis. To recreate them from raw data, put the 36 official ZIP files in `db1b_raw/` and run both `python process_db1b.py db1b_raw/DB1BMarket_2007_1.zip` and `python process_db1b_all_itineraries.py db1b_raw/DB1BMarket_2007_1.zip` for each year-quarter file. Compare raw ZIP hashes to `raw_file_sha256.txt`.
2. Run `python airline_case_quarterly.py`. This rewrites `airline_case_quarterly_results/results.json`, `quarterly_path.csv`, `window_estimates.csv`, and three route-match lists.
3. Run `python airline_case_robustness.py`. This writes `robustness.json` and `route_influence.csv`, and asserts that its nonstop fare estimates match the main analysis.
4. Run `python airline_case_composition.py` and `python airline_case_carrier_level.py`. These write `composition.json`, `composition_by_route.csv`, `carrier_level.json`, `carrier_level_matched_routes.csv`, and `carrier_level_path.csv`. The composition script asserts that its decomposition totals reproduce the published contrasts exactly.
5. Run `python build_airline_case_quarterly_pdf.py`. It creates `Airline_Merger_Expert_Style_Memo.pdf` in the folder. To use another destination, set `AIRLINE_MEMO_OUTPUT` to an absolute path.
6. For the Word version, run `python export_memo_content.py` then `node build_airline_case_quarterly_docx.js`. The second step needs the `docx` npm package (`npm install docx`) and the first needs `pdftoppm` to rasterize the chart. Set `AIRLINE_MEMO_DOCX` to choose another destination.

## Analysis decisions

- Keep domestic nonstop trips on a single coupon, drop bulk fares, and keep trips with positive passenger counts, fares between $50 and $2,000, and distances between 50 and 5,000 miles. Combine both directions of an airport pair into one route. Average the fare by passengers, first within each airline on a route in a quarter, then across airlines.
- Decide which routes count as overlaps using 2009 Q2 only, before the merger was announced: both airlines need at least 50 sampled passengers. That gives 24 routes. Requiring a fare in all 36 quarters keeps all 24 and leaves 106 AirTran-only candidates. That rule keeps only routes that survived the whole period, which is a limitation.
- Comparison routes need at least 50 AirTran passengers and no Southwest tickets in 2009 Q2. Each overlap route is paired with one of them, never reused, matched on 2009 Q2 fare, passengers, distance, and how concentrated the route is among airlines. Pairs must agree on whether an endpoint is in Florida, and how far apart a pair can be across all four traits combined is capped at 2.5 — that is a limit on the combined gap, not on route mileage. Twenty-four pairs remain. These AirTran-only routes were affected by the merger too, so the comparison only shows the extra difference on overlap routes.
- Balance is reported the standard way: the gap between the two groups divided by `sqrt((s_T^2 + s_C^2)/2)`, a measure of how spread out they are. An earlier version divided by the spread of the whole candidate pool instead, which includes the gap between the groups and every unused route, and so made the match look better than it was. On the main version that gave -0.20 on fare where the standard figure is -0.31.
- For the Southwest's-own-fare version, comparison routes are ones where Southwest and at least one airline other than AirTran each had 50 sampled passengers, and AirTran sold nothing. The second-airline rule is necessary: across all Southwest routes AirTran never touched, the typical route is 99% Southwest against 54% on the overlap routes, so without it the groups cannot be matched on concentration. This match does not require pairs to agree on Florida, which here costs more in fare balance than it buys. Region is the weak point of this version and is measured rather than assumed.
- The starting window is 2009 Q3 to 2010 Q2, the four full quarters before the September 27, 2010 announcement. Each later yearly figure averages four quarters, so all four seasons appear on both sides. Uncertainty comes from resampling whole route pairs 10,000 times.
- Check the trend before the merger by fitting a straight line through each pair's fare gap from 2007 Q1 to 2010 Q2, allowing for season. The alternative comparison routes are ones with two real airlines including JetBlue, Frontier, Spirit, Virgin America or Allegiant, and no AirTran or Southwest tickets; the Florida-only subset leaves 11 pairs.
- One extra version picks comparison routes partly by their fare trend from 2007 Q1 to 2009 Q2, holding out 2009 Q3-2010 Q2 as a check. It leaves 23 pairs. Because it uses the fare path itself to choose routes, it drags the later result toward the middle on its own, so it is a sensitivity check rather than a better estimate.

## Results

For 2015, measured against the four quarters before the September 2010 announcement, the route-average comparison gives **+1.3%** (range −4.9% to +8.1%). The 2013 figure is +9.0% (+4.0% to +13.9%), then it fades. But before the merger the overlap routes were already drifting apart from their comparison routes at **+2.9% a year** (+0.2% to +5.4%). That failed check matters more than whether the number after the merger happens to be positive.

Using other low-cost airlines as the comparison instead gives **+14.8%** (+7.9% to +22.1%), but those routes are much less alike geographically. Requiring pairs to agree on Florida leaves 11 pairs and gives +7.6% (−0.3% to +15.8%). Picking comparison routes by their early fare trend gives **−0.4%** (−6.6% to +6.5%). None of these is a verified effect of the merger.

Including connecting trips as well as nonstop, on the same routes, moves the 2015 figure to **+1.8%** (−4.3% to +8.3%), and the trend before the merger is still +3.4% a year. Dropping one overlap route at a time leaves it between −0.3% and +2.8%.

That last check is the wrong one to lead with. The fragile choice is *which routes count as overlaps*, not which single route gets dropped. The rule is 50 sampled passengers per airline, and since the data is a 10% sample that is about 500 real passengers a quarter. On four of the 24 routes the smaller airline carries under 10% of traffic, as little as 3.8% on Indianapolis–Las Vegas. Requiring 10% moves the figure to **+3.9%**; requiring 20% moves it to **+9.6%**. That is a much bigger swing than dropping routes one at a time suggests. Southwest's own fare barely moves under the same tests.

### Where the number actually comes from

If every airline keeps the fare it charged before the merger and only the share of passengers changes, that alone gives **+2.0%** against a **+1.3%** total, leaving **−0.7%** from airlines actually changing fares. The mix is more than the whole result. Southwest's fares on these routes were about 6.5% above AirTran's in 2009, so losing the AirTran name lifts a route average by itself. The other low-cost comparison is mostly real fare change (+9.4% of its +14.8%), so the versions disagree about the cause as well as the size.

### Southwest's own fare

Across 23 matched pairs, Southwest's own fare on the old overlap routes runs **+12.0%** (+6.7% to +17.9%) above comparable Southwest routes in 2015, and +14.0% in 2013. The trend before the merger is +1.4% a year (−1.4% to +4.5%) and a fake test on an early period gives −1.0% (−6.7% to +5.5%), so it passes the checks the route average fails. Every balance check is below 0.24, and dropping one route at a time leaves it between +10.8% and +13.0%.

The size, though, is not pinned down. 20 of the 23 overlap routes touch a Florida airport against only 10 of the 137 comparison candidates, so the match compares Florida routes with Western ones. Looking at comparison routes alone, where AirTran never flew, Southwest's fare rose 4.5% on Florida routes against 20.8% elsewhere — which pushes the unmatched version *down*. Forcing regional matching raises it to **+21.2%**, and the strict Florida-only version gives +25.5%, but both reuse 8 to 11 comparison routes with starting fares well out of line. Report the direction and the range, not a number.

Two more caveats carry real weight. Measuring from 2008 Q3–2009 Q2 instead halves the figure to +6.2%, because the gap was already +5.5% above the starting window by then; the fitted trend is flat but the path is not a straight line. And Southwest's own average is still an average over Southwest's tickets, and which tickets those were changed when AirTran's passengers moved across. Telling price apart from passenger mix needs fare-class data this project does not have.

The project does not measure consumer welfare, fares on connecting or newly added routes, service quality, optional fees, or damages. Network changes, costs, demand, and other mergers can hit the two groups differently. Requiring a fare in all 36 quarters keeps only routes that survived. Do not claim this study proves either harm or its absence.

## Research context and authorship

Primary documents are the DOJ merger closing statement (<https://www.justice.gov/archives/opa/pr/statement-department-justice-antitrust-division-its-decision-close-its-investigation>) and Southwest's merger announcement, closing, and final-flight notices (linked in the PDF). The memo compares the research question with Le (2016), DOI `10.1177/178359171601700302`, as summarized by GAO report `GAO-26-107740` (<https://www.gao.gov/products/gao-26-107740>).

The first version of this project was reviewed afterwards. It reproduced exactly, but the balance formula was wrong, two descriptions were inaccurate, and the headline number turned out to be mostly about which airline was selling tickets. The split and the Southwest's-own-fare version were added then, and the memo was rewritten around what the review found. `AUDIT.md` lists everything, including a mistake made during that rewrite and caught afterwards. Rerun the scripts and spot-check a few routes against the BTS files before relying on any figure here.

# What the review found

This is a record of the checks run on the first version of this project: what reproduced, what was wrong, and what changed. It is kept with the project because the mistakes are more useful than the estimates.

## Did it reproduce

I reran `airline_case_quarterly.py` and `airline_case_robustness.py` from the processed data in the repository. `results.json` came out identical. The CSV files differed only in the sixteenth decimal place, which is ordinary floating-point noise. The robustness script has a built-in check that it rebuilds the main numbers from the raw carrier files on its own, and that check passed. The earlier DOT airfare project reproduced exactly too.

I also checked the sources. GAO-26-107740 is real and does credit the 3.7% figure to Le. Le (2016) is in *Competition and Regulation in Network Industries* 17(3–4), pages 226–240, DOI `10.1177/178359171601700302`, and reports a range of 2.1% to 5.3%. The DOJ closing statement and Southwest's announcement and closing dates are as cited.

Nothing was calculated wrongly. Everything below is about what the numbers mean and how they were described.

## What was wrong

**1. The headline number was mostly about which airline was selling tickets.** The route average is an average across whichever airlines have tickets on that route. The merger removes one of them by 2015, so the average moves even if nobody changes a price. Splitting the number apart — freezing each airline's own fare and letting only passenger shares move — gives +2.0% from mix against a +1.3% total, leaving −0.7% from actual fares. Southwest's fares on these routes were about 6.5% above AirTran's in 2009, which is the whole story. The first version of the memo mentioned mix once, as one possible explanation among several, when it was bigger than the estimate itself.

*Fixed:* `airline_case_composition.py` does the split and checks its totals against the published numbers before reporting anything. The memo now leads with it.

**2. The robustness check on display was the wrong one.** "Dropping any one route leaves the estimate between −0.3% and +2.8%" sounds reassuring. But the fragile choice is not which route to drop, it is which routes count as overlaps at all. The rule is 50 sampled passengers per airline in 2009 Q2. Since the data is a 10% sample that is about 500 real passengers a quarter, and on four of the 24 routes the smaller airline carries under 10% of traffic — 3.8% on Indianapolis–Las Vegas, 5.4% on Detroit–Orlando, 5.5% on Baltimore–West Palm Beach, 6.8% on Baltimore–Seattle. Requiring 10% moves the estimate to +3.9%, and 20% moves it to +9.6%.

*Fixed:* that test is now computed in `airline_case_composition.py` and reported in the memo next to the drop-one-route range, for both versions of the analysis.

**3. The balance claim used the wrong denominator.** The balance check divided by the spread of the whole pool of candidate routes, which includes the gap between the groups and all the unused comparison routes. That makes the match look better than it is. Using the standard formula, the main version's fare balance is −0.31, not −0.20, and the other low-cost version — the one producing +14.8% — is off by +0.73 on distance.

*Fixed:* `airline_case_quarterly.py` now uses the standard formula, with a comment recording the change. Only the reported balance figures moved. No estimate changed.

**4. Two descriptions were inaccurate.** "A 2.5-standard-deviation distance limit" reads as a limit on route mileage. It is actually a limit on how far apart a pair can be across all four matching traits combined. And the last scheduled AirTran flight left Atlanta on December 28, 2014 — December 29 is the date of Southwest's press release. The earlier project said December 28, so the two documents disagreed with each other.

*Fixed:* both corrected in the memo and the README.

**5. A known problem went unnamed.** One version picks comparison routes using the fare path itself before the merger. Doing that drags the later result toward the middle on its own, whichever direction the truth lies in. Calling it "exploratory" is not the same as saying why it is biased.

*Fixed:* named in the note under the results table.

**6. The document could drift away from the analysis.** The percentages in the memo's text were typed in by hand while the tables were computed from `results.json`. Rerunning on different data would have left the text asserting numbers the analysis no longer supported.

*Fixed:* every figure in the memo is now read from the results files when the document is built. A check confirms that all 69 signed percentages in the finished PDF trace back to a value in one of those files.

## What was added

`airline_case_carrier_level.py` changes both the measure and the comparison group at once. The measure is Southwest's own fare, so no other airline can affect it. The comparison routes are ones where Southwest and at least one airline other than AirTran both carried real traffic in 2009 Q2, and AirTran sold nothing. That second-airline requirement is not cosmetic: across all Southwest routes AirTran never touched, the typical route is 99% Southwest, against 54% on the overlap routes, so without it the two groups cannot be matched on concentration at all.

Across 23 matched pairs the 2015 figure is +12.0% (+6.7%, +17.9%). The trend before the merger is +1.4% a year (−1.4%, +4.5%), a fake test on an early period gives −1.0% (−6.7%, +5.5%), every balance check is below 0.24, dropping one route at a time leaves it between +10.8% and +13.0%, and changing the overlap definition barely moves it. It passes the checks the route-average version fails.

It is still not proof of anything, and the memo says so. AirTran chose where to compete with Southwest. The comparison routes were affected by the merger too. And Southwest's own average is still an average over Southwest's tickets, and which tickets those were changed when AirTran's passengers moved across — separating price from passenger mix needs fare-class data this project does not have. Measuring from 2008 Q3–2009 Q2 instead of the four quarters before the announcement halves the figure to +6.2%, because the path before the merger is not a straight line even where the fitted trend is flat.

## 7. A mistake made during the rewrite itself

The new version, as first written, dropped the requirement that a pair agree on whether an endpoint is in Florida, and justified it by saying that averaging four quarters holds season fixed. That reasoning is wrong. Averaging quarters handles *season*. It does nothing about *region*.

It mattered. 20 of the 23 overlap routes touch a Florida airport, but only 10 of the 137 comparison candidates do, because Southwest's other competitive routes are concentrated in the West. So the match ended up pairing Orlando–Pittsburgh with Denver–Midway, and Fort Lauderdale–Pittsburgh with San Diego–Seattle. A test on comparison routes alone — where AirTran never flew — shows Southwest's fare rising 4.5% on Florida routes and 20.8% everywhere else between the starting window and 2015. The regions did not move together, and the two groups sat on opposite sides of that gap.

The error pushed the number down, not up, so +12.0% was understated rather than flattering. Forcing regional matching raises it to +21.2%, and the strict Florida-only version gives +25.5%, but both reuse 8 to 11 Florida comparison routes and have starting fares well out of line. The size cannot be pinned down from this pool of routes.

*Fixed:* `airline_case_carrier_level.py` now measures the regional makeup of both groups, runs the comparison-routes-only test, and builds a region-matched version, and its own summary says the size is not pinned down. The memo reports a positive difference of roughly 12% to 21% with the regional problem stated up front, instead of a single number. The bad reasoning is gone.

This is the most instructive finding in the project: a problem caught in the preferred version of the analysis, after that version had already produced a satisfying result.

## What is still breakable

The regional makeup of the comparison pool is the binding constraint and it is only measured here, not solved. A real fix needs either a wider pool of Florida routes or a model with region-by-period effects instead of one-to-one matching. The uncertainty ranges resample route pairs, so they describe noise *given* the pairs chosen, not the risk of having chosen the wrong ones. Requiring a fare in all 36 quarters keeps only routes that survived the whole period, in both versions. Seats flown, fuel and airport costs, demand, bag and seat fees, connecting options, service quality, and any benefit on routes Southwest added afterwards are all outside this test. None of that is fixed by rewording.

# Final evaluation protocol

Protocol: `forecast-inventory-v1`; frozen before executing the additional evaluation.

The `weekly-rolling-v2` predictors and validation-selection rule remain unchanged.
No winner is changed using the already inspected 2018–2019 test outcomes. The
Croston candidate is described as SBA-style (alpha 0.1, correction 0.95); dense
series behaviour and signed bias are reported. This is additional evidence, not
a newly untouched forecast test set.

## Forecast reporting

Reproduce the five candidates on the original public CSV and retain complete
one- through four-week prediction paths for the existing validation, calibration
and test origins. Verify the reproduced aggregate metrics against the frozen
benchmark. Report naive, recent-four-week mean, selected and ML-everywhere, signed
bias and interval coverage. The selection objective includes all four leads;
the main report retains 1-, 2- and 4-week results.

Use 10,000 paired circular block bootstrap replicates, seed 20261107, eight-origin
blocks, seven blocks truncated to 52 positions. Common sampled time indices are
used across methods, categories and horizons. Recompute per-series WAPE before
equal-weight aggregation. Report percentile 95% ranges. These are temporal
resampling ranges in one pharmacy, not site-transfer or company-performance bounds.

## Conditional forecast-driven inventory replay

Use the original chronological weekly category-sales observations as a demand
proxy. No synthetic residuals are substituted for the observed demand path.
Replay naive, recent4, validation-selected and ML forecasts from the same origins.
At the start of each week, receive due lots, remove expired lots, place an order
using the available three-week forecast sum plus a buffer, then serve observed
weekly demand by FEFO. Inventory position includes all outstanding incoming stock.
Lost demand does not become an undocumented backlog.

Fixed assumptions, identical for every method and buffer:

- 200 paired logistics seeds, beginning at 20261108.
- Seven buffers: 0, 0.25, 0.5, 1, 1.5, 2 and 3 weeks of the next-week forecast.
- Weekly review; delivery lead 1 week with probability 0.7, otherwise 2 weeks.
- Weekly supplier capacity is 1.8 times the 95th percentile of the preceding
  52 historical weeks, with a 10% disruption probability reducing it to 60%.
  Capacity is based on past observations, never the future true demand mean.
- Arrival shelf life is uniformly 13–52 weeks; no pharmaceutical shelf-life
  distribution or real supply permission is inferred from this assumption.
- Common opening inventory is three times the preceding 52-week median. First
  four weeks are warm-up and excluded from scored outcomes in each partition.
- Check conservation, nonnegative stock, fulfilment at most observed demand,
  and no use of future actual demand in ordering.

Choose the smallest buffer reaching each predeclared 95% and 98% calibration
fill target, averaging the paired seeds over the existing calibration period.
Freeze that choice before reporting the test period. If none qualifies, report
unavailable. A calibration target is not a guaranteed test service level.

Report all seven held-out frontier points and the calibration-chosen policies'
held-out fill, stock, unmet demand and expiry. Aggregate stock in weeks of the
historical reference volume, not by adding unlike category units. Seed ranges
reflect simulated logistics variability on the fixed observed demand path.
Any matched-service comparison selected from a displayed test frontier is
explicitly descriptive, not a deployable policy selected without test exposure.

This is a conditional one-pharmacy/category replay with invented supply conditions,
not a causal field trial, observed distributor stock history, company savings or
proof of the official targets. Do not tune assumptions or remove adverse results
because they fail to show a desired improvement. Actual GRD policies, data and
pilot baselines remain required.

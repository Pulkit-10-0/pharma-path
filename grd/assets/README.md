# Observed public pharmacy benchmark and final evaluation

`pharma-salesdaily.csv` contains 2,106 original-date daily category records from
2014-01-02 through 2019-10-08. Fractional publisher quantities are preserved.
Source: Milan Zdravkovic, *Pharma Sales Data*, Kaggle:
https://www.kaggle.com/datasets/milanzdravkovic/pharma-sales-data

The catalogue records CC BY-NC 4.0. Confirm appropriate rights before commercial
operation. The publisher preprocessed missing values and outliers. These are
category sales from one pharmacy, not observed Assam SKU/site demand. The public
CSV never enters the Assam operating ledger.

The manifest fingerprint covers the exact included CSV bytes. The previous
manifest's mismatching fingerprint was corrected; the input CSV did not change.

## Files

- `pharma-benchmark.json`: all five candidates, selected on validation, with 52
  final test origins per 1/2/4-week lead across all eight categories.
- `pharma-backtest-paths.json.gz`: dated calibration/test actuals and complete
  recursive prediction paths, with reproduction checks against frozen scores.
- `pharma-evaluation.json`: means, medians, bias, individual comparisons and
  10,000 paired eight-origin bootstrap ranges, seed 20261107.
- `pharma-inventory-replay.json`: chronological sales/forecast replay under
  declared synthetic supply conditions, 200 paired logistics seeds, seven
  buffers and calibration-chosen policies with unfiltered test outcomes.
- `assam-opening.json`: generated dynamic scenario opening batches for isolated
  rehearsals; synthetic CC0, entirely separate from the observed pharmacy data.

Reproduce, with the pinned environment, from the repository root:

```sh
PYTHONPATH=. OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  python scripts/evaluate_final_evidence.py --output /path/to/new-output
```

To independently regenerate the original candidate report:

```sh
PYTHONPATH=. OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  python scripts/evaluate_public_benchmark.py --output /path/to/new-benchmark.json
```

The predictors/selection are unchanged. The all-24 comparison is 27.31% selected
WAPE versus 32.92% last week and 29.59% four-week mean. ML everywhere scores 26.82%
with more negative average bias. Selection is not retuned on that test.
The bootstrap concerns time in one pharmacy, not other sites. Conditional stock
replay is not a GRD outcome, currency saving or proof of the official targets.

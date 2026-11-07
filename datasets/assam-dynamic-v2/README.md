# Assam dynamic supply scenario v2

This is **entirely generated data**, dedicated to the public domain under CC0-1.0.
It contains no patient, customer or private GRD records. Packs, prices, events,
coordinates and operating policies are illustrative assumptions.

- **218,400 demand observations:** 12 medicine presentations × 5 fictional sites ×
  1,820 days × 2 measures (requested and sales).
- **109,200 daily stock and signal rows**, covering 260 complete weeks from
  **8 November 2021 through 1 November 2026**.
- Four distributors (Guwahati, Dibrugarh, Silchar and Jorhat) supplied by a
  fictional central warehouse. Location codes describe scenarios, not premises.

## Files

| File | Purpose |
| --- | --- |
| `demand.csv.gz` | Forecasting observations: date, product code, location code, quantity, measure and base unit. Extract the gzip file to open the CSV in Excel. |
| `daily_operations.csv.gz` | Daily opening/closing inventory, receipts, dispatches, expiry, requested demand, fulfilled sales, unmet demand, remaining transit and generation signals. |
| `events.json` | Assumed promotion and local demand-shock windows, with their multipliers. |
| `catalogue.json` | Product labels, units, carton conversions, assumed costs and generation parameters. |
| `manifest.json` | Version, seed, dates, counts, hashes, checks and limitations. |

## What changes over time

Demand combines weekday behaviour, different seasonal patterns by product,
growth, persistent increases/decreases in demand, promotions, temporary local
spikes/drops, correlated noise and overdispersion. One item has intermittent
demand; a newly introduced item has explicitly inactive days before launch.
These are simulated events, not claims about actual weather, outbreaks or
commercial promotions in Assam.

The inventory simulation fulfils only available stock. It reorders in carton
multiples, allocates warehouse stock using first-expiry-first-out (FEFO), moves
that same quantity into the distributor's delivery pipeline, and receives it
after a variable lead time. Disruption windows extend delivery times. Supplier
orders replenish the central warehouse. Shortages and expiry can therefore
arise from the generated demand and supply process rather than independent
random stock numbers.

Every daily row satisfies:

```text
opening + receipts - sales - dispatches - expiry = closing
requested - sales = unmet
0 <= sales <= requested
```

Daily closing stock carries into the following day's opening. Internal
warehouse dispatches equal distributor receipts plus remaining pipeline. The
warehouse has zero customer-demand observations; adding its transfers to
distributor demand would double-count the same supply chain.

## How the application uses it

The installer adds versioned product IDs and source-tagged requested/sales
observations. Forecasting uses **requested** demand so a stockout does not
masquerade as low demand. Event columns explain how the data was generated;
the current forecasting models use demand lags and calendar features, and do
**not** consume these event flags. No claim of promotion-aware ML is made.

The history's final unexpired physical batches become the new products' opening
stock through explicit stock movements. Historical pipeline is retained in the
export for reconciliation but is **not an approved live order** or an actionable
incoming shipment. New orders use the application's normal approval/dispatch/
receipt workflow. Existing products, orders, stock movements and receipts remain
available with their original IDs; the earlier catalogue is labelled accordingly.

Reproduce the files from the repository root:

```sh
python -m grd.cli export-dynamic-scenario --output datasets/assam-dynamic-v2
```

Install once in an existing, dated synthetic Assam workspace:

```sh
python -m grd.cli add-dynamic-scenario --email demo@pharmapath.local
```

The installer refuses a real/shadow workspace. Repeated calls reuse the existing
dataset. The same seed and cutoff reproduce the file hashes; installation stores
the content hash in the database's source register. Forecast jobs are queued for
the main product at four distributors and the other products at Silchar.

This scenario exercises product behaviour and data consistency. Accuracy and
business impact measured here **do not predict a real distributor pilot**. The
separate observed public pharmacy benchmark is unchanged.

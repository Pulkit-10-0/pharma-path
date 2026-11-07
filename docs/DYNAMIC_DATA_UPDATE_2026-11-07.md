# Dynamic dataset and laptop navigation update — 7 November 2026

The previous default strip history was generated using a smooth seasonal Poisson
rate. Its low test errors were evidence about that simple generator. The current
scenario introduces more varied operating conditions while retaining explicit
synthetic provenance.

## New default operating history

- 12 product presentations, five sites, 260 complete weeks.
- 218,400 separate requested/sales observations and 109,200 daily operations rows.
- Weekday patterns, product-specific seasonality, growth, persistent demand-level
  changes, promotions, temporary shocks, intermittent demand and a product launch.
- Stock-constrained sales, explicit unmet requests, FEFO batches, variable lead
  times, disruption delays, supplier replenishment and expiry.
- Daily and cross-site conservation checks, unique dates and deterministic hashes.

The source files, dictionary, assumptions and regeneration command are in
[`datasets/assam-dynamic-v2`](../datasets/assam-dynamic-v2/README.md). Generated
events are explanatory metadata, not evaluated external ML inputs. Forecasts use
requested history and are re-evaluated on the new series; the previous 96%
coverage value does not carry over to the new product's results.

The installer adds new product identities and source-tagged observations. It
preserves previous orders, receipts, quantities and reservations; earlier
catalogue entries are labelled. The final generated physical batches become
auditable opening stock for the new catalogue. Historical pipeline is retained
in the exported history rather than fabricated as a live confirmed order.

The old operating datasets contain 23,870 observations. Including them, the
upgraded workspace has 242,270 observations. The observed public pharmacy
benchmark remains separate and unchanged.

## Navigation

The fixed sidebar uses the viewport's dynamic height. Its menu can scroll
independently while the account and assistant controls stay available. Shorter
viewports use smaller gaps and padding; the brand stays on one line. Mobile
retains the existing navigation drawer.

## Verification

- Backend suite: 72 passed; one existing PostgreSQL-specific test skipped locally.
- Web suite: 29 passed; TypeScript and production build passed.
- Full generated export checked for pre-launch inactive stock and content hashes.
- Candidate database installed with 242,270 demand observations and 18 catalogue
  entries (12 current, six earlier); forecasts evaluated through the worker.
- Live database backed up privately before installation; all existing stock and
  reservations verified unchanged after the new dataset was committed.
- Browser layout checks at 1440×900, 1366×650, 1280×560 and 1024×600.

This is generated operational evidence. It does not establish real GRD accuracy
or pilot impact, and no forecast metric was chosen as a generation target.

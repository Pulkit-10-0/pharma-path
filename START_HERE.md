# Pharma Path: evaluator quick start

[Live website](https://pharma-path.onrender.com/) ·
[Source](https://github.com/Pulkit-10-0/pharma-path-nesfic) ·
[Official NESFIC-I-09 challenge](https://startup.assam.gov.in/nesfic26/problem-statements/nesfic-i-09)

Pharma Path connects medicine demand forecasting with stock decisions and a
traceable approval → dispatch → receipt workflow. It has a planner website,
an Android field client and a shared backend with a reconciled stock ledger.

## Explore the hosted workspace

The website pre-fills the owner's shared synthetic login. Click **Sign in to
workspace**. The free API host can need about a minute to wake after inactivity.
Use the current Paracetamol **10-tablet strip** presentation; earlier scenarios
are explicitly labelled and retain their existing orders.

1. **Network:** inspect available stock, projected shortages and site locations.
2. **Forecasts:** select Silchar, compare operating methods, test error and interval
   coverage. The current operating series has 260 complete weeks and 52 test
   origins. Model selection uses validation, separate from calibration and test.
3. **Planning / Action centre:** compare sources, quantities, arrival dates,
   shelf life and the effect on donor stock. Approve a feasible action, dispatch
   stock and record the receiving site's actual receipt.
4. **Inventory / Operations desk:** inspect batches, exceptions, supplier orders,
   returns and counted quantities. Actions are explicit, with an audit trail.
5. **Data sources / Stock & evidence:** distinguish the generated operating
   history, public observed benchmark and assumptions behind policy simulations.

The public login can change the shared synthetic workspace, so numbers and open
actions may differ between visits. The application does not mark a shipment
delivered merely because its expected delivery date has passed.

## Evidence and boundaries

| Item | What is available | Qualification |
| --- | --- | --- |
| Current operating data | 218,400 requested/sales observations; 109,200 daily stock/signal rows; 12 presentations, five sites, five years | Generated assumptions, not observed GRD or Assam transactions |
| Dynamic behaviour | Demand shocks, promotions, changing demand levels, a product launch, intermittent demand, delayed replenishment, shortages and expiry | Generator event flags are explanatory metadata, not external inputs to the current forecasting model |
| Stock consistency | Daily balances and cross-site transfers reconcile; final physical batches initialise the current catalogue | Historical remaining transit is not fabricated as an approved live shipment |
| Independent forecasting | Eight public pharmacy categories, three horizons, 52 test origins per comparison | Approximately 17% relative WAPE reduction versus repeating last week; below the challenge's 20% target, and not GRD's baseline |
| Policy comparison | Service/inventory frontier under the same simulated demand and delays | Single-lane synthetic assumptions; not measured distributor savings |
| Android | Shared API, scoped access, encrypted caching and a durable pending-action queue | Existing APK evidence is emulator-based; a physical-phone camera/QR test and recording remain pending |

[Dataset files and dictionary](datasets/assam-dynamic-v2/README.md) ·
[Complete project README](README.md) ·
[Implementation status](docs/PRD_STATUS.md) ·
[Submission code review](docs/SUBMISSION_CODE_REVIEW_2026-11-07.md)

## Run this source locally

Follow [README: local setup](README.md#13-local-setup). Install the locked Python
dependencies, set your private `.env`, migrate, and run:

```sh
grd seed-demo --email demo@pharmapath.local --as-of 2026-11-01
grd add-pack-scenario --email demo@pharmapath.local
grd add-dynamic-scenario --email demo@pharmapath.local
```

Build `web`, start `grd serve`, then start `grd worker` in a second terminal. Open
http://127.0.0.1:8011/. Sign in using your locally configured password. The
pre-filled public password belongs to the hosted workspace; local development
can use its own configured sign-in.

The root notebook and numbered CSV scripts preserve the original experiment.
The current application runs through `grd/`, `web/`, `shared/` and `mobile/`.
Attribution and publication history are in [SOURCE_ORIGIN](docs/SOURCE_ORIGIN.md).

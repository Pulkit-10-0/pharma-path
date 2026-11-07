# Pharma Path: evaluator quick start

[Live website](https://pharma-path.onrender.com/) · [Product review and video](https://pharma-path.onrender.com/review/index.html) · [Final release](https://github.com/Pulkit-10-0/pharma-path-nesfic/releases/tag/nesfic-i09-final-v1.4.0) · [Official challenge](https://startup.assam.gov.in/nesfic26/problem-statements/nesfic-i-09)

Pharma Path connects a demand forecast to stock planning, approval, dispatch and receiver-confirmed receipt. The main submission includes the website, Android field app and Power BI analysis. Power BI retains its historical experiment scope; its metrics are not the current operating or public-benchmark results.

## Access

The public synthetic account is pre-filled. Click **Sign in to workspace**. The default creates an independent two-hour rehearsal. Its generated email appears in the sidebar; enter that email on Android with the public evaluation password to join the same stock records. Maximum three concurrent rehearsals. If capacity is reached, untick isolation to explore the shared synthetic account. Never enter private company data here.

The Free API can take about a minute to wake. The static review page and downloadable materials provide an alternative while it starts. The readiness schedule does not guarantee uninterrupted hosting.

## One current-data journey

1. **Network:** choose Paracetamol 500 mg, 10-tablet strips. Dibrugarh opens with 488 strips and about 4.8 days of nominal cover, with a projected shortage on 6 November at the fixed 1 November rehearsal date.
2. **Planning:** compare no action with 1,640 strips (82 cartons) from the central warehouse. The rehearsal assumes two-day express arrival on 3 November, before the shortage. The recipient's projected gap falls to zero; this does not remove other sites' risks.
3. **Action centre:** approve the comparison, dispatch the allocated batches and open the shipment QR. **Android:** scan the clean shipment label and record a checked receipt. These are recorded rehearsal handoffs, not proof a real vehicle moved.
4. **Inventory:** verify stock movements, batch states and reconciliation. Partial/damaged receipts, returns, supplier receipts and count exceptions are separate explicit actions.
5. **Stock & evidence / Forecasts:** inspect the public benchmark and forecast-driven stock replay. Main-product markers use forecasts at four distributors; other combinations can use the explicitly labelled historical-mean fallback.

## Evidence today

- Generated operating data: **48 distributor-product requested-demand series × 260 weeks**, with requested demand and sales stored separately. No private GRD or observed Assam demand is included.
- Observed public benchmark: eight categories, 1/2/4-week horizons, 52 held-out origins each. Selected mean WAPE 27.31% versus 32.92% last week and 29.59% four-week mean. Relative improvements **17.0% and 7.7%**. The 20% official target is not met by the point estimate.
- Paired time-block bootstrap: 10,000 samples, eight-origin blocks, seed 20261107. The 13.5–21.3% range reflects time variation in one pharmacy, not uncertainty across GRD sites.
- Stock replay: 200 paired supply seeds, seven buffers, forecast-driven ordering, calibration-only policy choices and held-out service/stock. Supply, lead times and shelf life are assumptions; no measured savings are claimed.
- Coverage varies 61.5–98.1% against 90% nominal. The planner does not turn intervals into shortage probabilities. Selected bias averages −4.26%; ML everywhere has lower final-test WAPE and more negative bias. The known test was not used to retune selection.
- The release verification JSON records the exact website/API/APK source, CI, checksums and physical-device test boundary. Android source support alone is not proof of field acceptance. Native iOS is outside scope.

See [release identity and limits](docs/RELEASE_RECORD.md), [dataset dictionary](datasets/assam-dynamic-v2/README.md), [full README](README.md) and [local setup](README.md#13-local-setup). Reproduce the final evaluation with `PYTHONPATH=. python scripts/evaluate_final_evidence.py` after installing locked dependencies.

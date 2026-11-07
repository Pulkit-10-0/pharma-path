"""Reproducible synthetic demand and a conserving, multi-site supply history.

These are invented stress scenarios, never observed Assam/GRD records. Event
flags explain generation; they are not supplied to the current forecaster.
"""

from collections import defaultdict, deque
from datetime import date, timedelta
import csv
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
from sqlalchemy import insert, select

from . import domain as d
from .models import Batch, Dataset, Demand, Job, Location, Organisation, Product, User

VERSION = "assam-dynamic-v2"
SEED = 20261107
WEEKS = 260
SITES = ("central", "guwahati", "dibrugarh", "silchar", "jorhat")
SITE_WEIGHTS = (0, 1.15, 0.90, 1.0, 0.72)
# Every price, pack, event and volume below is an illustrative assumption.
CATALOGUE = (
    ("paracetamol", "Paracetamol 500 mg · 10-tablet strips", "strip", 20, 900, 190, 0.28),
    ("cetirizine", "Cetirizine 10 mg · 10-tablet strips", "strip", 20, 1800, 85, 0.32),
    ("ors", "ORS · 21 g sachets", "sachet", 100, 1400, 140, 0.45),
    ("amoxicillin", "Amoxicillin 500 mg · 10-capsule strips", "strip", 20, 5500, 65, 0.22),
    ("metformin", "Metformin 500 mg · 10-tablet strips", "strip", 50, 2100, 150, 0.07),
    ("amlodipine", "Amlodipine 5 mg · 10-tablet strips", "strip", 50, 2200, 110, 0.05),
    ("pantoprazole", "Pantoprazole 40 mg · 10-tablet strips", "strip", 20, 4500, 95, 0.12),
    ("salbutamol", "Salbutamol · 100 mcg inhalers", "inhaler", 12, 12000, 18, 0.35),
    ("zinc", "Zinc 20 mg · 10-tablet strips", "strip", 20, 2400, 42, 0.33),
    ("cough", "Cough preparation · 100 mL bottles", "bottle", 24, 6500, 28, 0.38),
    ("slow", "Specialty supplement · 10-tablet strips", "strip", 20, 8500, 1.2, 0.12),
    ("new", "Vitamin C 500 mg · 10-tablet strips", "strip", 20, 3200, 55, 0.18),
)


def _take(lots, quantity, latest=None):
    """Consume FEFO without a negative batch; optionally require arrival shelf life."""
    taken = []
    remaining = int(quantity)
    for lot in sorted(lots, key=lambda x: (x["expiry"], x["code"])):
        if latest is not None and lot["expiry"] <= latest:
            continue
        amount = min(lot["quantity"], remaining)
        if amount:
            lot["quantity"] -= amount
            remaining -= amount
            taken.append({**lot, "quantity": amount})
        if not remaining:
            break
    lots[:] = [lot for lot in lots if lot["quantity"]]
    return taken


def generate(as_of=date(2026, 11, 1), weeks=WEEKS, seed=SEED):
    """Return portable rows, signals and final physical batches from one simulation."""
    if as_of.weekday() != 6 or weeks < 12:
        raise ValueError("Use a Sunday cutoff and at least 12 complete weeks")
    days = weeks * 7
    start = as_of - timedelta(days=days - 1)
    ledger, final_lots, event_log = [], {}, []
    for pi, (sku, name, unit, pack, cost, base, amplitude) in enumerate(CATALOGUE):
        # Independent streams keep existing products stable if catalogue order changes.
        rng = np.random.default_rng([seed, int.from_bytes(hashlib.sha256(sku.encode()).digest()[:4])])
        histories = [deque(maxlen=28) for _ in SITES]
        launch_index = max(0, days - 730) if sku == "new" else 0
        for li in range(1, 5):
            histories[li].extend([0 if launch_index else base * SITE_WEIGHTS[li]] * 28)
        lots = [[] for _ in SITES]
        pending = [[] for _ in SITES]
        arrivals = defaultdict(list)
        for li in range(5):
            qty = int(base * (sum(SITE_WEIGHTS) * 40 if li == 0 else SITE_WEIGHTS[li] * 13))
            if launch_index:
                qty = 0
            lots[li] = [{"code": f"D2-{sku}-{li}-opening", "quantity": qty,
                         "expiry": start + timedelta(days=240)}]
        noise = np.zeros(5)
        promos, shocks = [], []
        for year in range((days + 364) // 365):
            for li in range(1, 5):
                pstart = year * 365 + int(rng.integers(30, 300))
                promos.append((li, pstart, pstart + 14, float(rng.uniform(1.15, 1.60))))
                sstart = year * 365 + int(rng.integers(35, 320))
                shocks.append((li, sstart, sstart + int(rng.integers(7, 22)),
                               float(rng.choice([0.55, 0.70, 1.6, 2.0]))))
        for kind, events in (("promotion", promos), ("local_demand_shock", shocks)):
            for li, first, last, multiplier in events:
                if first < days:
                    event_log.append({"product_code": sku, "location_code": SITES[li], "kind": kind,
                                      "start": str(start + timedelta(days=first)),
                                      "end": str(start + timedelta(days=min(last, days - 1))),
                                      "multiplier": round(multiplier, 4)})
        for i in range(days):
            day = start + timedelta(days=i)
            opening = [sum(x["quantity"] for x in group) for group in lots]
            receipts = [0] * 5
            for li, lot in arrivals.pop(i, []):
                lots[li].append(lot)
                receipts[li] += lot["quantity"]
            for group in pending:
                group[:] = [(when, qty) for when, qty in group if when > i]
            expired = [0] * 5
            for li in range(5):
                expired[li] = sum(x["quantity"] for x in lots[li] if x["expiry"] <= day)
                lots[li][:] = [x for x in lots[li] if x["expiry"] > day and x["quantity"]]
            requests, sales, flags = [0] * 5, [0] * 5, [{} for _ in SITES]
            # A generated regional disruption repeats at varying times, independent
            # of any observed weather or public health information.
            disruption = 190 <= (i + pi * 11) % 365 <= 201
            for li in range(1, 5):
                active = i >= launch_index
                promo = next((m for site, a, b, m in promos if site == li and a <= i <= b), 1.0)
                shock = next((m for site, a, b, m in shocks if site == li and a <= i <= b), 1.0)
                noise[li] = 0.70 * noise[li] + rng.normal(0, 0.14)
                seasonal = 1 + amplitude * np.sin(2 * np.pi * (day.timetuple().tm_yday - pi * 19) / 365.25)
                weekday = (1.15, 1.10, 1.02, 1.04, 1.13, 0.94, 0.54)[day.weekday()]
                growth = 0.88 + 0.24 * i / max(1, days - 1)
                regime = 1.0 if i < days * 0.55 else (1.20 if (li + pi) % 2 else 0.80)
                intensity = base * SITE_WEIGHTS[li] * seasonal * weekday * growth * regime
                intensity *= promo * shock * np.exp(noise[li]) * rng.gamma(7, 1 / 7)
                if sku == "slow" and rng.random() < 0.70:
                    intensity = 0.0
                requests[li] = int(rng.poisson(max(0, intensity))) if active else 0
                histories[li].append(requests[li])
                sales[li] = sum(x["quantity"] for x in _take(lots[li], requests[li]))
                flags[li] = {"product_active": int(active), "promotion_active": int(promo != 1),
                             "promotion_multiplier": round(promo, 4), "demand_shock_multiplier": round(shock, 4),
                             "regime_multiplier": regime}
            dispatched = [0] * 5
            for li in range(1, 5):
                rate = float(np.mean(histories[li]))
                cover = sum(x["quantity"] for x in lots[li]) + sum(q for _, q in pending[li])
                lead = 1 if li == 1 else 4
                extra_delay = int(rng.integers(4, 10)) if disruption else int(rng.choice([0, 0, 0, 1, 2]))
                if day.weekday() in (0, 3) and cover < rate * (lead + 6):
                    order = int(np.ceil(max(0, rate * (lead + 14) - cover) / pack)) * pack
                    parts = _take(lots[0], order, day + timedelta(days=lead + extra_delay + 30))
                    amount = sum(x["quantity"] for x in parts)
                    dispatched[0] += amount
                    for part in parts:
                        arrivals[i + lead + extra_delay].append((li, part))
                    if amount:
                        pending[li].append((i + lead + extra_delay, amount))
                flags[li]["supply_disruption"] = int(disruption)
            aggregate = sum(float(np.mean(histories[li])) for li in range(1, 5))
            central_position = sum(x["quantity"] for x in lots[0]) + sum(q for _, q in pending[0])
            if day.weekday() in (1, 4) and central_position < aggregate * 22:
                quantity = int(np.ceil(max(0, aggregate * 42 - central_position) / pack)) * pack
                lead = int(rng.integers(7, 13)) + (7 if disruption else 0)
                if quantity:
                    arrivals[i + lead].append((0, {"code": f"D2-{sku}-{i}", "quantity": quantity,
                                                  "expiry": day + timedelta(days=365 if sku != "slow" else 100)}))
                    pending[0].append((i + lead, quantity))
            for li in range(5):
                closing = sum(x["quantity"] for x in lots[li])
                if opening[li] + receipts[li] - expired[li] - sales[li] - dispatched[li] != closing:
                    raise AssertionError("Daily stock conservation failed")
                ledger.append({"date": str(day), "product_code": sku, "location_code": SITES[li],
                               "base_unit": unit, "requested_quantity": requests[li], "sales_quantity": sales[li],
                               "unmet_quantity": requests[li] - sales[li], "opening_stock": opening[li],
                               "receipts": receipts[li], "expired_quantity": expired[li],
                               "dispatched_quantity": dispatched[li], "closing_stock": closing,
                               "in_transit_quantity": sum(q for _, q in pending[li]),
                               "weekday": day.weekday(),
                               **({"product_active": 1, "promotion_active": 0, "promotion_multiplier": 1.0,
                                   "demand_shock_multiplier": 1.0, "regime_multiplier": 1.0,
                                   "supply_disruption": int(disruption)} if li == 0 else flags[li])})
        for li, site in enumerate(SITES):
            final_lots[(sku, site)] = [dict(lot) for lot in lots[li]]
    digest = hashlib.sha256()
    for row in ledger:
        digest.update((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())
    manifest = {
        "name": "Assam dynamic supply scenario v2", "generator_version": VERSION,
        "evidence_type": "synthetic", "seed": seed, "as_of": str(as_of),
        "first_date": str(start), "complete_weeks": weeks, "products": len(CATALOGUE),
        "locations": len(SITES), "row_count": len(ledger) * 2, "daily_stock_rows": len(ledger),
        "content_sha256": digest.hexdigest(),
        "source_url": "https://github.com/Pulkit-10-0/pharma-path/tree/main/datasets/assam-dynamic-v2",
        "licence": "Project-generated synthetic data, CC0-1.0", "geography": "Five fictional Assam operating sites",
        "units": "product_base_units",
        "dynamic_factors": ["weekday patterns", "annual seasonality", "growth and regime changes",
                            "local demand shocks", "promotions", "correlated overdispersed noise",
                            "new-product introduction", "intermittent demand", "delayed supply",
                            "FEFO expiry", "stock-constrained sales"],
        "checks": {"daily_stock_conservation": True, "sales_at_most_requested": True,
                   "unmet_equals_requested_less_sales": True, "no_negative_stock": True,
                   "unique_series_dates": True},
        "limitations": ["Invented operating data; not observed Assam or GRD demand",
                        "Events, packs, prices, supply policies and volumes are illustrative assumptions",
                        "Event flags explain generation; the current forecast uses demand history, not these flags",
                        "Warehouse dispatches are internal transfers, not additional customer demand",
                        "Remaining historical in-transit supply is excluded from actionable opening stock and live orders",
                        "Forecast accuracy and policy impact on this scenario do not predict a real pilot"],
        "summary": {"unmet_quantity": sum(r["unmet_quantity"] for r in ledger),
                    "stockout_days": sum(r["unmet_quantity"] > 0 for r in ledger),
                    "promotion_days": sum(r["promotion_active"] for r in ledger),
                    "disruption_days": sum(r["supply_disruption"] for r in ledger),
                    "expired_quantity": sum(r["expired_quantity"] for r in ledger)},
    }
    return ledger, final_lots, event_log, manifest


def export(output, as_of=date(2026, 11, 1), weeks=WEEKS, seed=SEED):
    ledger, _, events, manifest = generate(as_of, weeks, seed)
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    # mtime=0 makes compressed artifacts byte-for-byte reproducible.
    import io
    for filename, fields, rows in (
        ("daily_operations.csv.gz", list(ledger[0]), ledger),
        ("demand.csv.gz", ["date", "product_code", "location_code", "quantity", "measure", "base_unit"],
         ({"date": r["date"], "product_code": r["product_code"], "location_code": r["location_code"],
           "quantity": r[f"{measure}_quantity"], "measure": measure, "base_unit": r["base_unit"]}
          for r in ledger for measure in ("requested", "sales"))),
    ):
        with (out / filename).open("wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0, filename="") as gz:
            with io.TextIOWrapper(gz, encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
    manifest["files"] = {name: hashlib.sha256((out / name).read_bytes()).hexdigest()
                         for name in ("demand.csv.gz", "daily_operations.csv.gz")}
    (out / "events.json").write_text(json.dumps(events, indent=2) + "\n")
    (out / "catalogue.json").write_text(json.dumps([
        dict(zip(("code", "name", "base_unit", "carton_size", "unit_cost_paise", "daily_rate_assumption",
                  "seasonal_amplitude_assumption"), p)) for p in CATALOGUE
    ], indent=2) + "\n")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def install(s, email, *, weeks=WEEKS, seed=SEED, queue_forecasts=True):
    """Add a versioned scenario, preserving every existing SKU, stock movement and order."""
    user = s.scalar(select(User).where(User.email == email.lower(), User.active, User.role == "admin"))
    if not user:
        raise ValueError("An active administrator is required")
    org = s.scalar(select(Organisation).where(Organisation.id == user.org_id).with_for_update())
    if org.mode != "synthetic" or org.scenario_on is None:
        raise ValueError("Dynamic scenarios may only be added to a dated synthetic workspace")
    existing = next((x for x in s.scalars(select(Dataset).where(Dataset.org_id == org.id))
                     if x.provenance.get("generator_version") == VERSION), None)
    if existing:
        return {"dataset_id": existing.id, "row_count": existing.row_count, "already_installed": True}
    prefix = org.id[:8]
    locations = [s.get(Location, prefix + "-L" + str(i)) for i in range(5)]
    if not all(loc and loc.org_id == org.id for loc in locations):
        raise ValueError("The original five Assam scenario locations are required")
    ledger, final_lots, _, manifest = generate(org.scenario_on, weeks, seed)
    dataset = Dataset(org_id=org.id, name=manifest["name"], digest=manifest["content_sha256"],
                      provenance=manifest, row_count=manifest["row_count"])
    s.add(dataset)
    # Keep prior workflow references resolvable, with unambiguous catalogue names.
    earlier_ids = [prefix + "-P" + str(i) for i in range(5)] + [prefix + "-P-strips"]
    for previous in s.scalars(select(Product).where(Product.org_id == org.id, Product.id.in_(earlier_ids))):
        previous.name += " · earlier scenario"
        previous.provenance = {**previous.provenance, "archived_scenario": True, "superseded_by": VERSION}
    products = {}
    for sku, name, unit, pack, cost, _, _ in CATALOGUE:
        product = Product(id=f"{prefix}-D2-{sku}", org_id=org.id, name=name,
                          base_unit=unit, pack_size=pack, unit_cost_paise=cost,
                          unit_conversions={"carton": pack},
                          provenance={"evidence_type": "synthetic", "generator_version": VERSION,
                                      "scenario_priority": 2 if sku == "paracetamol" else 0,
                                      "review_start_location": locations[3].id if sku == "paracetamol" else None,
                                      "note": "Invented pack, price and history; not a GRD product record"})
        s.add(product)
        products[sku] = product
    s.flush()
    site_ids = dict(zip(SITES, (loc.id for loc in locations)))
    chunk = []
    for row in ledger:
        for measure in ("requested", "sales"):
            chunk.append({"org_id": org.id, "date": date.fromisoformat(row["date"]),
                          "product_id": products[row["product_code"]].id,
                          "location_id": site_ids[row["location_code"]], "measure": measure,
                          "quantity": row[f"{measure}_quantity"], "dataset_id": dataset.id})
        if len(chunk) >= 1000:
            s.execute(insert(Demand), chunk)
            chunk = []
    if chunk:
        s.execute(insert(Demand), chunk)
    # The history's closing physical batches become auditable opening stock.
    # Historical pipeline is not silently counted as actual confirmed supply.
    for (sku, site), group in final_lots.items():
        if not group:
            group = [{"code": f"D2-{sku}-{site}-empty", "quantity": 0,
                      "expiry": org.scenario_on + timedelta(days=180)}]
        for lot in group:
            batch = Batch(org_id=org.id, product_id=products[sku].id, location_id=site_ids[site],
                          code=lot["code"], expiry=lot["expiry"], quantity=0, reserved=0)
            s.add(batch)
            s.flush()
            d.change(s, user, batch, lot["quantity"], "synthetic_history_opening", dataset.id)
    jobs = []
    if queue_forecasts:
        for sku, product in products.items():
            for li in (range(1, 5) if sku == "paracetamol" else (3,)):
                job = Job(org_id=org.id, actor_id=user.id, kind="forecast", payload={
                    "product_id": product.id, "location_id": locations[li].id,
                    "as_of": str(org.scenario_on), "measure": "requested", "horizons": [1, 2, 4]})
                s.add(job)
                jobs.append(job)
    org.revision += 1
    d.audit(s, user, "synthetic.dynamic_scenario_added", dataset.id, manifest, site_ids.values())
    s.flush()
    return {"dataset_id": dataset.id, "row_count": dataset.row_count,
            "product_ids": {sku: p.id for sku, p in products.items()},
            "job_ids": [job.id for job in jobs], "already_installed": False}

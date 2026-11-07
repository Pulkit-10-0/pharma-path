"""Auditable temporal bootstrap and conditional forecast-driven inventory replay.

Predictors/selection are frozen. Observed sales are a demand proxy; all supply
conditions are invented. These results are not company savings or a field trial.
"""

from datetime import datetime
import csv
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .forecasting import VERSION, evaluation_windows, metric, replay

PROTOCOL = "forecast-inventory-v1"
METHODS = ("naive", "recent4", "selected", "ml")
BUFFERS = (0, 0.25, 0.5, 1, 1.5, 2, 3)
TARGETS = (95, 98)
BOOTSTRAP_SEED = 20261107
LOGISTICS_SEED = 20261108


def paths_from_source(source, frozen_report):
    """Reproduce every frozen candidate score and retain dated forecast paths."""
    with Path(source).open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    dates = pd.to_datetime([datetime.strptime(row["datum"], "%m/%d/%Y") for row in rows])
    archive = {
        "protocol": PROTOCOL,
        "algorithm": VERSION,
        "source_sha256": hashlib.sha256(Path(source).read_bytes()).hexdigest(),
        "selection_unchanged": True,
        "categories": {},
    }
    if archive["source_sha256"] != frozen_report["sha256"]:
        raise ValueError("Source CSV does not match the frozen benchmark")
    for category, reference in frozen_report["categories"].items():
        frame = pd.DataFrame({"date": dates, "quantity": [float(row[category]) for row in rows]})
        weekly = frame.groupby(pd.Grouper(key="date", freq="W-SUN")).agg(
            quantity=("quantity", "sum"), days=("date", "nunique")
        )
        weekly = weekly[weekly.days == 7]
        values = weekly.quantity.to_numpy(dtype=float)
        ends = [x.date() for x in weekly.index]
        windows = evaluation_windows(len(values), 4)
        result = {
            "selected": reference["selected"],
            "zero_demand_weeks": int((values == 0).sum()),
            "complete_weeks": len(values),
            "partitions": {},
        }
        for partition in ("calibration", "test"):
            origins = windows[partition]
            past = values[max(0, origins.start - 52):origins.start]
            paths = {}
            for method in reference["validation_mae"]:
                actual, predicted = replay(values, ends, origins, (1, 2, 3, 4), method)
                paths[method] = predicted.tolist()
                if partition == "test":
                    for lead in (1, 2, 4):
                        check = metric(actual[:, lead - 1], predicted[:, lead - 1])
                        for name in ("wape_pct", "bias_pct", "mae"):
                            if not np.isclose(check[name], reference["test"][str(lead)][method][name], atol=1e-8):
                                raise ValueError(f"Frozen benchmark reproduction failed: {category}/{method}/{lead}/{name}")
            result["partitions"][partition] = {
                "issued_after_week_ending": [str(ends[o - 1]) for o in origins],
                "first_target_week_ending": [str(ends[o]) for o in origins],
                "actual": actual.tolist(),
                "predictions": paths,
                "historical_reference_mean": float(past.mean()),
                "historical_reference_median": float(np.median(past)),
                "weekly_supplier_capacity": float(1.8 * np.quantile(past, 0.95)),
            }
        archive["categories"][category] = result
        print(f"Reproduced paths: {category}", flush=True)
    return archive


def bootstrap_report(archive, frozen_report, replicates=10000, block=8, seed=BOOTSTRAP_SEED):
    """Pair time indices across every method/category/lead; never resample sites."""
    categories = list(archive["categories"])
    actual = np.asarray([archive["categories"][c]["partitions"]["test"]["actual"] for c in categories])
    predicted = {}
    for method in METHODS:
        predicted[method] = np.asarray([
            archive["categories"][c]["partitions"]["test"]["predictions"][
                archive["categories"][c]["selected"] if method == "selected" else method
            ] for c in categories
        ])
    n = actual.shape[1]
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, n, size=(replicates, int(np.ceil(n / block))))
    indices = ((starts[:, :, None] + np.arange(block)) % n).reshape(replicates, -1)[:, :n]
    horizons = [1, 2, 4]
    groups = {str(h): [h - 1] for h in horizons} | {"all": [0, 1, 3]}
    errors = {m: np.abs(actual - p) for m, p in predicted.items()}
    output = {
        "protocol": PROTOCOL,
        "source_sha256": archive["source_sha256"],
        "configuration": {"replicates": replicates, "block_origins": block, "seed": seed, "test_origins": n},
        "scope": "Paired temporal resampling in one pharmacy; categories fixed, no sites resampled; not GRD bounds",
        "groups": {},
        "comparisons": [],
    }
    for name, leads in groups.items():
        points = {m: 100 * errors[m][:, :, leads].sum(axis=1) / actual[:, :, leads].sum(axis=1) for m in METHODS}
        # Batches bound temporary memory on the Free host and during reproduction.
        samples = {m: [] for m in METHODS}
        for start in range(0, replicates, 128):
            idx = indices[start:start + 128]
            denominator = actual[:, idx, :][:, :, :, leads].sum(axis=2)
            for m in METHODS:
                numerator = errors[m][:, idx, :][:, :, :, leads].sum(axis=2)
                samples[m].extend((100 * numerator / denominator).mean(axis=(0, 2)).tolist())
        means = {m: float(points[m].mean()) for m in METHODS}
        reductions = {}
        for reference in ("naive", "recent4"):
            paired = 100 * (1 - np.asarray(samples["selected"]) / np.asarray(samples[reference]))
            reductions[reference] = {
                "relative_reduction_pct": 100 * (1 - means["selected"] / means[reference]),
                "interval_95_pct": np.quantile(paired, [0.025, 0.975]).tolist(),
            }
        output["groups"][name] = {
            "mean_wape_pct": means,
            "median_wape_pct": {m: float(np.median(p)) for m, p in points.items()},
            "mean_bias_pct": {m: float((100 * (predicted[m] - actual)[:, :, leads].sum(axis=1) / actual[:, :, leads].sum(axis=1)).mean()) for m in METHODS},
            "selected_relative_reduction": reductions,
        }
    for category, info in frozen_report["categories"].items():
        for lead in horizons:
            selected = info["test"][str(lead)][info["selected"]]
            naive = info["test"][str(lead)]["naive"]
            output["comparisons"].append({
                "category": category, "lead_weeks": lead, "selected_method": info["selected"],
                "selected_wape_pct": selected["wape_pct"], "naive_wape_pct": naive["wape_pct"],
                "selected_bias_pct": selected["bias_pct"],
                "selected_coverage_pct": 100 * selected["interval_coverage"],
                "relative_reduction_pct": 100 * (1 - selected["wape_pct"] / naive["wape_pct"]),
            })
    return output


def inventory_replay(partition, method, buffer_weeks, seed, warmup=4, trace=False):
    """Orders depend only on dated predictions, current stock and past capacity."""
    actual = np.asarray(partition["actual"], dtype=float)[:, 0]
    forecasts = np.asarray(partition["predictions"][method], dtype=float)
    n = len(actual)
    if n <= warmup:
        raise ValueError("Replay requires observations after warm-up")
    reference = partition["historical_reference_mean"]
    opening = 3 * partition["historical_reference_median"]
    capacity = partition["weekly_supplier_capacity"]
    rng = np.random.default_rng(seed)
    leads = np.where(rng.random(n) < 0.7, 1, 2)
    capacities = capacity * np.where(rng.random(n) < 0.1, 0.6, 1)
    shelves = rng.integers(13, 53, size=n)
    lots, pipeline = [[opening, 26]], []
    placed = served_all = expired_all = 0.0
    served = unmet = holding = expired = 0.0
    shortage_weeks, orders = 0, []
    for week, demand in enumerate(actual):
        for arrival, quantity, expiry in pipeline:
            if arrival == week:
                lots.append([quantity, expiry])
        pipeline = [x for x in pipeline if x[0] > week]
        loss = sum(q for q, expiry in lots if expiry <= week)
        expired_all += loss
        lots = [[q, expiry] for q, expiry in lots if expiry > week and q > 1e-10]
        stock_before = sum(q for q, _ in lots)
        target = max(0.0, float(forecasts[week, :3].sum() + buffer_weeks * forecasts[week, 0]))
        requested = max(0.0, target - stock_before - sum(x[1] for x in pipeline))
        accepted = min(requested, float(capacities[week]))
        if accepted > 1e-10:
            arrival = week + int(leads[week])
            pipeline.append((arrival, accepted, arrival + int(shelves[week])))
            placed += accepted
        remaining = float(demand)
        for lot in sorted(lots, key=lambda x: x[1]):
            take = min(lot[0], remaining)
            lot[0] -= take
            remaining -= take
        supplied = demand - remaining
        served_all += supplied
        stock_after = sum(q for q, _ in lots)
        if week >= warmup:
            served += supplied
            unmet += remaining
            expired += loss
            holding += (stock_before + stock_after) / 2
            shortage_weeks += int(remaining > 1e-7)
        if trace:
            orders.append({"week": week, "target": target, "requested": requested, "accepted": accepted})
    closing = sum(q for q, _ in lots)
    transit = sum(x[1] for x in pipeline)
    if not np.isclose(opening + placed, served_all + expired_all + closing + transit, atol=1e-6):
        raise AssertionError("Replay failed stock conservation")
    total = float(actual[warmup:].sum())
    return {
        "fill_rate_pct": 100 * served / total if total else None,
        "average_stock_weeks": holding / (n - warmup) / reference if reference else None,
        "unmet_quantity": unmet,
        "expired_quantity": expired,
        "shortage_weeks": shortage_weeks,
        "conservation_ok": True,
        **({"orders": orders} if trace else {}),
    }


def inventory_report(archive, seeds=200):
    """Select buffers on calibration; show unfiltered held-out frontiers as well."""
    by_category = {}
    aggregate = {m: [[] for _ in BUFFERS] for m in METHODS}
    for category, source in archive["categories"].items():
        cal, test = source["partitions"]["calibration"], source["partitions"]["test"]
        methods = {}
        for label in METHODS:
            method = source["selected"] if label == "selected" else label
            calibration, tests = [], []
            for bi, buffer in enumerate(BUFFERS):
                cr = [inventory_replay(cal, method, buffer, LOGISTICS_SEED + i) for i in range(seeds)]
                tr = [inventory_replay(test, method, buffer, LOGISTICS_SEED + 1000000 + i) for i in range(seeds)]
                calibration.append(cr)
                tests.append(tr)
                aggregate[label][bi].append(tr)
            points = []
            for buffer, runs in zip(BUFFERS, tests):
                points.append({
                    "buffer_weeks": buffer,
                    **{key: float(np.mean([r[key] for r in runs])) for key in ("fill_rate_pct", "average_stock_weeks", "unmet_quantity", "expired_quantity", "shortage_weeks")},
                    "logistics_seed_range_95_fill_pct": np.quantile([r["fill_rate_pct"] for r in runs], [0.025, 0.975]).tolist(),
                })
            choices = {}
            for target in TARGETS:
                choice = next((i for i, runs in enumerate(calibration) if np.mean([r["fill_rate_pct"] for r in runs]) >= target), None)
                choices[str(target)] = None if choice is None else {
                    "buffer_weeks": BUFFERS[choice],
                    "calibration_fill_pct": float(np.mean([r["fill_rate_pct"] for r in calibration[choice]])),
                    "test": points[choice],
                }
            methods[label] = {"forecast_method": method, "frontier": points, "calibration_selected_policies": choices}
        by_category[category] = methods
        print(f"Replayed inventory: {category} ({seeds} paired seeds)", flush=True)
    frontiers = {}
    for label in METHODS:
        points = []
        for buffer, groups in zip(BUFFERS, aggregate[label]):
            # Equal category weight; preserve the paired logistics seed positions.
            fills = np.mean([[r["fill_rate_pct"] for r in group] for group in groups], axis=0)
            stocks = np.mean([[r["average_stock_weeks"] for r in group] for group in groups], axis=0)
            points.append({"buffer_weeks": buffer, "fill_rate_pct": float(fills.mean()), "average_stock_weeks": float(stocks.mean()), "logistics_seed_range_95_fill_pct": np.quantile(fills, [0.025, 0.975]).tolist()})
        frontiers[label] = points
    chosen = {}
    for target in TARGETS:
        chosen[str(target)] = {}
        for label in METHODS:
            policies = [methods[label]["calibration_selected_policies"][str(target)] for methods in by_category.values()]
            available = [p for p in policies if p is not None]
            chosen[str(target)][label] = {
                "categories_qualified_on_calibration": len(available),
                "categories_total": len(policies),
                "test_fill_pct": float(np.mean([p["test"]["fill_rate_pct"] for p in available])) if available else None,
                "test_average_stock_weeks": float(np.mean([p["test"]["average_stock_weeks"] for p in available])) if available else None,
                "categories_meeting_target_on_test": sum(p["test"]["fill_rate_pct"] >= target for p in available),
            }
    return {
        "protocol": PROTOCOL,
        "evidence_type": "conditional_observed_sales_synthetic_supply_replay",
        "measured_grd_impact": False,
        "configuration": {"seeds": seeds, "seed": LOGISTICS_SEED, "independent_test_seed_offset": 1000000, "buffer_weeks": list(BUFFERS), "calibration_targets_pct": list(TARGETS), "warmup_weeks": 4, "arrival_shelf_life_weeks": [13, 52], "lead_weeks": [1, 2], "supplier_capacity": "1.8 x past 52-week 95th percentile; 10% weeks reduced to 60%"},
        "source_sha256": archive["source_sha256"],
        "frontiers": frontiers,
        "calibration_selected_summary": chosen,
        "categories": by_category,
        "limitations": [
            "One pharmacy's observed category sales are a demand proxy, not uncensored Assam SKU demand",
            "Logistics, supplier capacity, shelf lives and opening stock are assumptions; category units are not verified packs",
            "Forecast methods and validation selection are unchanged; the forecast test period has already been inspected",
            "Buffers are chosen on calibration only; test targets can fail and are not guaranteed",
            "Seed ranges reflect invented logistics on a fixed chronological demand path, not future-site uncertainty",
            "Mean stock is normalised by preceding historical demand; no currency saving or official target is established",
        ],
    }


def save_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def save_paths(path, data):
    raw = (json.dumps(data, separators=(",", ":"), allow_nan=False) + "\n").encode()
    Path(path).write_bytes(gzip.compress(raw, mtime=0))

import copy

import numpy as np
import pytest

from grd.evaluation import bootstrap_report, inventory_report, inventory_replay
from grd.forecasting import metric


def fixture_archive(n=52):
    actual = np.repeat(np.arange(10, 10 + n, dtype=float)[:, None], 4, axis=1)
    predictions = {m: (actual * factor).tolist() for m, factor in (("naive", 1.2), ("recent4", 1.1), ("ml", 1.05))}
    partition = {"actual": actual.tolist(), "predictions": predictions,
                 "historical_reference_mean": 10.0, "historical_reference_median": 10.0,
                 "weekly_supplier_capacity": 18.0}
    archive = {"source_sha256": "test", "categories": {"A": {"selected": "recent4", "partitions": {"calibration": copy.deepcopy(partition), "test": partition}}}}
    scores = {str(h): {m: {**metric(actual[:, h - 1], np.asarray(p)[:, h - 1]), "interval_coverage": 0.9} for m, p in predictions.items()} for h in (1, 2, 4)}
    report = {"categories": {"A": {"selected": "recent4", "test": scores}}}
    return archive, report


def test_bootstrap_recomputes_paired_ratios_and_is_repeatable():
    archive, report = fixture_archive()
    first = bootstrap_report(archive, report, replicates=128)
    assert first == bootstrap_report(archive, report, replicates=128)
    for group in first["groups"].values():
        reduction = group["selected_relative_reduction"]["naive"]
        assert reduction["relative_reduction_pct"] == pytest.approx(50)
        assert reduction["interval_95_pct"] == pytest.approx([50, 50])
        assert group["selected_relative_reduction"]["recent4"]["relative_reduction_pct"] == pytest.approx(0)


def test_inventory_order_does_not_see_current_or_future_actual_demand():
    archive, _ = fixture_archive(20)
    p = archive["categories"]["A"]["partitions"]["test"]
    first = inventory_replay(p, "naive", 1, 42, trace=True)
    changed = copy.deepcopy(p)
    changed["actual"][0][0] = 100000
    other = inventory_replay(changed, "naive", 1, 42, trace=True)
    assert first["orders"][0] == other["orders"][0]
    assert first["conservation_ok"] and other["conservation_ok"]
    assert 0 <= other["fill_rate_pct"] <= 100
    assert first["unmet_quantity"] < other["unmet_quantity"]


def test_inventory_policy_choices_are_frozen_from_calibration():
    archive, _ = fixture_archive(20)
    a = inventory_report(archive, seeds=2)
    changed = copy.deepcopy(archive)
    for row in changed["categories"]["A"]["partitions"]["test"]["actual"]:
        row[0] *= 20
    b = inventory_report(changed, seeds=2)
    for method in ("naive", "recent4", "selected", "ml"):
        left = a["categories"]["A"][method]["calibration_selected_policies"]
        right = b["categories"]["A"][method]["calibration_selected_policies"]
        for target, policy in left.items():
            assert (policy is None) == (right[target] is None)
            if policy:
                assert policy["buffer_weeks"] == right[target]["buffer_weeks"]
                assert policy["calibration_fill_pct"] == right[target]["calibration_fill_pct"]
    assert a["measured_grd_impact"] is False

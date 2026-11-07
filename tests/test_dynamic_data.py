from datetime import date

import pytest
from sqlalchemy import func, select

from grd.db import transaction
from grd.dynamic_data import CATALOGUE, generate, install
from grd.models import Batch, Dataset, Demand, Location, Organisation, Product


def test_dynamic_history_has_complete_dates_conserving_stock_and_unconstrained_requests():
    rows, lots, events, manifest = generate(weeks=12)
    assert len(rows) == 12 * 7 * 5 * len(CATALOGUE)
    assert manifest["row_count"] == len(rows) * 2
    assert len({(r["date"], r["product_code"], r["location_code"]) for r in rows}) == len(rows)
    last = {}
    warehouse_dispatches = distributor_receipts = 0
    for r in rows:
        key = r["product_code"], r["location_code"]
        if key in last:
            assert r["opening_stock"] == last[key]["closing_stock"]
        assert r["opening_stock"] + r["receipts"] - r["sales_quantity"] - r["expired_quantity"] - r["dispatched_quantity"] == r["closing_stock"]
        assert 0 <= r["sales_quantity"] <= r["requested_quantity"]
        assert r["unmet_quantity"] == r["requested_quantity"] - r["sales_quantity"]
        assert r["closing_stock"] >= 0 and r["in_transit_quantity"] >= 0
        if r["location_code"] == "central":
            assert r["requested_quantity"] == r["sales_quantity"] == 0
            warehouse_dispatches += r["dispatched_quantity"]
        else:
            distributor_receipts += r["receipts"]
        last[key] = r
    assert warehouse_dispatches == distributor_receipts + sum(r["in_transit_quantity"] for (sku, site), r in last.items() if site != "central")
    for key, group in lots.items():
        assert sum(lot["quantity"] for lot in group) == last[key]["closing_stock"]
        assert all(lot["expiry"] > date(2026, 11, 1) for lot in group)
    assert events
    assert any(r["unmet_quantity"] > 0 for r in rows)
    assert generate(weeks=12)[3]["content_sha256"] == manifest["content_sha256"]
    assert generate(weeks=12, seed=123)[3]["content_sha256"] != manifest["content_sha256"]


def test_dynamic_install_is_idempotent_and_preserves_existing_stock(env):
    with transaction(env.app.state.factory) as s:
        org = s.get(Organisation, "org")
        org.scenario_on = date(2026, 11, 1)
        for i in range(5):
            s.add(Location(id=f"org-L{i}", org_id="org", name=str(i), kind="warehouse" if i == 0 else "distributor", district="Assam"))
    with transaction(env.app.state.factory) as s:
        result = install(s, "admin@example.test", weeks=12, queue_forecasts=False)
    with transaction(env.app.state.factory) as s:
        assert s.get(Batch, "B-SOURCE").quantity == 50
        assert s.get(Product, "P").name == "Demo product"
        dataset = s.get(Dataset, result["dataset_id"])
        assert dataset.row_count == s.scalar(select(func.count()).select_from(Demand).where(Demand.dataset_id == dataset.id))
        repeat = install(s, "admin@example.test", weeks=12)
        assert repeat["already_installed"] is True
        assert repeat["dataset_id"] == dataset.id
    assert env.client.get("/api/v1/inventory/reconciliation", headers=env.headers).json()["ok"]


def test_dynamic_install_refuses_real_workspaces(env):
    with transaction(env.app.state.factory) as s:
        s.get(Organisation, "org").mode = "shadow"
    with transaction(env.app.state.factory) as s:
        with pytest.raises(ValueError, match="synthetic"):
            install(s, "admin@example.test", weeks=12)

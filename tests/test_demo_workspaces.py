from datetime import date, timedelta

import pytest
from sqlalchemy import select

from grd import demo_workspaces as dw
from grd.db import transaction
from grd.dynamic_data import generate, install
from grd.models import Batch, Location, Organisation, Workflow, now


@pytest.fixture
def template(env, monkeypatch):
    monkeypatch.setenv("GRD_DEMO_EMAIL", "admin@example.test")
    _, lots, _, manifest = generate(weeks=12)
    opening = {"generator_version": manifest["generator_version"], "scenario_on": manifest["as_of"],
               "content_sha256": manifest["content_sha256"], "row_count": manifest["row_count"],
               "batches": [{"product_code": sku, "location_code": site, **lot, "expiry": str(lot["expiry"])}
                           for (sku, site), batches in lots.items() for lot in batches]}
    monkeypatch.setattr(dw, "opening_snapshot", lambda: opening)
    with transaction(env.app.state.factory) as s:
        s.get(Organisation, "org").scenario_on = date(2026, 11, 1)
        for i in range(5):
            s.add(Location(id=f"org-L{i}", org_id="org", name=str(i), kind="warehouse" if i == 0 else "distributor", district="Assam"))
    with transaction(env.app.state.factory) as s:
        install(s, "admin@example.test", weeks=12, queue_forecasts=False)
    return env


def login(env, isolated=True):
    return env.client.post("/api/v1/auth/login", json={"email": "admin@example.test", "password": "test-password-123", "isolated_demo": isolated})


def test_isolated_rehearsals_copy_versioned_data_without_touching_template(template):
    a, b = login(template), login(template)
    assert a.status_code == b.status_code == 200
    assert 7100 < a.json()["expires_in"] <= 7200
    ah = {"Authorization": "Bearer " + a.json()["access_token"]}
    bh = {"Authorization": "Bearer " + b.json()["access_token"]}
    am = template.client.get("/api/v1/me", headers=ah).json()
    bm = template.client.get("/api/v1/me", headers=bh).json()
    assert am["organisation_id"] != bm["organisation_id"] != "org"
    assert am["demo_session"]["isolated"] is True
    ab = template.client.get("/api/v1/inventory/batches", headers=ah).json()["items"]
    bb = template.client.get("/api/v1/inventory/batches", headers=bh).json()["items"]
    assert ab and bb and not ({x["id"] for x in ab} & {x["id"] for x in bb})
    denied = template.client.post("/api/v1/inventory/batches/" + ab[0]["id"] + "/status", headers={**bh, "Idempotency-Key": "cross"}, json={"status": "quarantined", "reason": "cross-tenant attempt"})
    assert denied.status_code == 404
    with transaction(template.app.state.factory) as s:
        assert s.get(Batch, "B-SOURCE").quantity == 50
    assert template.client.get("/api/v1/inventory/reconciliation", headers=ah).json()["ok"]
    assert template.client.get("/api/v1/inventory/reconciliation", headers=template.headers).json()["ok"]


def test_capacity_is_bounded_but_shared_sign_in_still_works(template):
    for _ in range(3):
        assert login(template).status_code == 200
    assert login(template).status_code == 429
    assert login(template, False).status_code == 200


def test_expired_rehearsals_are_rejected_and_only_their_records_are_removed(template):
    response = login(template).json()
    headers = {"Authorization": "Bearer " + response["access_token"]}
    me = template.client.get("/api/v1/me", headers=headers).json()
    identifier = me["organisation_id"]
    with transaction(template.app.state.factory) as s:
        marker = s.scalar(select(Workflow).where(Workflow.org_id == identifier, Workflow.kind == dw.KIND))
        marker.payload = {**marker.payload, "expires_at": (now() - timedelta(minutes=1)).isoformat()}
    assert template.client.get("/api/v1/me", headers=headers).status_code == 401
    assert login(template).status_code == 200
    with transaction(template.app.state.factory) as s:
        assert s.get(Organisation, identifier) is None
        assert s.get(Organisation, "org") is not None
        assert s.get(Batch, "B-SOURCE").quantity == 50


def test_shadow_tenant_cannot_create_synthetic_rehearsal(template):
    with transaction(template.app.state.factory) as s:
        s.get(Organisation, "org").mode = "shadow"
    assert login(template).status_code == 403

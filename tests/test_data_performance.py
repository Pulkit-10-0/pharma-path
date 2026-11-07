import csv
from datetime import date, timedelta
import io
import json

import pytest
from sqlalchemy import event, select

from grd.db import transaction
from grd.models import Demand, User

META = {
    "name": "Bulk import fixture",
    "source_url": "test",
    "licence": "Synthetic test",
    "geography": "Fictional network",
    "evidence_type": "synthetic",
    "units": "tablet",
    "limitations": ["Generated test observations"],
}


def upload(env, raw, dry_run=True, headers=None):
    return env.client.post(
        "/api/v1/imports/demand",
        headers=headers or env.headers,
        data={"metadata": json.dumps(META), "dry_run": str(dry_run).lower()},
        files={"file": ("demand.csv", raw, "text/csv")},
    )


def csv_rows(count, location="DEST", measure="requested"):
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["date", "product_id", "location_id", "quantity", "measure"])
    for i in range(count):
        writer.writerow([str(date(2024, 1, 1) + timedelta(days=i)), "P", location, 10, measure])
    return out.getvalue().encode()


def test_large_import_uses_bounded_reads_and_commits_all_observations(env):
    statements = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(env.app.state.engine, "before_cursor_execute", capture)
    try:
        response = upload(env, csv_rows(400), dry_run=False)
    finally:
        event.remove(env.app.state.engine, "before_cursor_execute", capture)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["committed"] and result["valid_rows"] == 400 and result["source_total"] == 4000
    # Database reads should not grow by one or more queries per observation.
    assert len(statements) < 20
    assert upload(env, csv_rows(400), dry_run=False).json()["duplicate"] is True


def test_import_row_limit_is_rejected_before_catalogue_lookups(env):
    response = upload(env, csv_rows(10_001))
    assert response.status_code == 413, response.text
    assert env.client.get("/api/v1/datasets", headers=env.headers).json()["total"] == 0


def test_overlapping_import_rejects_the_whole_file(env):
    assert upload(env, csv_rows(2), dry_run=False).json()["committed"]
    result = upload(env, csv_rows(3), dry_run=False).json()
    assert not result["committed"]
    assert result["invalid_rows"] == 2 and result["valid_rows"] == 1
    with transaction(env.app.state.factory) as s:
        assert not s.scalar(select(Demand).where(Demand.date == date(2024, 1, 3)))


def test_replayed_import_checks_current_site_scope(env):
    raw = b"date,product_id,location_id,quantity,measure\n2024-01-01,P,DEST,10,requested\n2024-01-01,P,OTHER,20,requested\n"
    assert upload(env, raw, dry_run=False).json()["committed"]
    with transaction(env.app.state.factory) as s:
        s.get(User, "operator").role = "steward"
    result = upload(env, raw, dry_run=False, headers=env.operator).json()
    assert not result["committed"] and not result.get("duplicate")
    assert any("not accessible" in error["error"] for error in result["errors"])


def test_demand_pages_load_only_the_requested_page_and_keep_stable_order(env):
    loaded = []

    def capture(target, context):
        loaded.append(target.id)

    event.listen(Demand, "load", capture)
    try:
        response = env.client.get(
            "/api/v1/demand",
            params={"product_id": "P", "location_id": "DEST", "offset": 5, "limit": 2},
            headers=env.headers,
        )
    finally:
        event.remove(Demand, "load", capture)
    assert response.status_code == 200, response.text
    page = response.json()
    assert page["total"] == 28 and len(page["items"]) == 2
    assert len(loaded) == 2
    repeated = env.client.get(
        "/api/v1/demand",
        params={"product_id": "P", "location_id": "DEST", "offset": 5, "limit": 2},
        headers=env.headers,
    ).json()
    assert repeated["items"] == page["items"]


def test_demand_measure_and_date_filters_preserve_separate_series(env):
    with transaction(env.app.state.factory) as s:
        for i in range(7):
            s.add(
                Demand(
                    org_id="org",
                    product_id="P",
                    location_id="DEST",
                    date=date(2026, 10, 26) + timedelta(days=i),
                    quantity=3,
                    measure="sales",
                    dataset_id="sales-fixture",
                )
            )
    params = {"product_id": "P", "location_id": "DEST", "start": "2026-10-26", "end": "2026-11-01"}
    for measure, quantity in (("requested", 10), ("sales", 3)):
        result = env.client.get(
            "/api/v1/demand", params={**params, "measure": measure}, headers=env.headers
        ).json()
        assert result["total"] == 7 and sum(row["quantity"] for row in result["items"]) == 7 * quantity
    assert env.client.get("/api/v1/demand", params=params, headers=env.headers).json()["total"] == 14
    assert (
        env.client.get(
            "/api/v1/demand", params={**params, "location_id": "SOURCE"}, headers=env.operator
        ).status_code
        == 403
    )


@pytest.mark.parametrize(
    "extra",
    [
        {"offset": -1},
        {"limit": 201},
        {"limit": 0},
        {"measure": "supplied"},
        {"start": "2026-11-02", "end": "2026-11-01"},
    ],
)
def test_demand_query_rejects_invalid_filters(env, extra):
    assert (
        env.client.get(
            "/api/v1/demand", params={"product_id": "P", "location_id": "DEST", **extra}, headers=env.headers
        ).status_code
        == 422
    )

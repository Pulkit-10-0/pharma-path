"""Bounded isolated synthetic rehearsals; never reset a shared or company tenant."""

from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path

from sqlalchemy import case, delete, func, insert, literal, select

from . import domain as d
from .models import Base, Batch, Dataset, Demand, Job, Location, Organisation, Product, Route, User, Workflow, now

MAX_WORKSPACES = 3
LIFETIME_HOURS = 2
KIND = "demo_session"


def opening_snapshot():
    return json.loads((Path(__file__).with_name("assets") / "assam-opening.json").read_text())


def session_info(s, user, org):
    marker = s.scalar(select(Workflow).where(Workflow.org_id == org.id, Workflow.kind == KIND))
    if not marker:
        return None
    expires = datetime.fromisoformat(marker.payload["expires_at"])
    if expires <= datetime.now(timezone.utc):
        d.fail("This rehearsal has expired. Start a fresh workspace from the public sign-in.", 401)
    return {"isolated": True, "expires_at": marker.payload["expires_at"], "email": user.email,
            "template": marker.payload["template"], "note": "Independent synthetic stock; expires after two hours"}


def purge_expired(s, template_org):
    markers = list(s.scalars(select(Workflow).where(Workflow.kind == KIND)))
    live = 0
    for marker in markers:
        if marker.payload.get("origin_org_id") != template_org.id:
            continue
        org = s.get(Organisation, marker.org_id)
        if org is None or org.mode != "synthetic" or not marker.payload.get("disposable"):
            continue
        expires = datetime.fromisoformat(marker.payload["expires_at"])
        if expires > datetime.now(timezone.utc):
            live += 1
            continue
        running = s.scalar(select(Job.id).where(Job.org_id == org.id, Job.status == "running").limit(1))
        if running:
            live += 1
            continue
        # Only organisations created and marked by this helper are disposable.
        for table in reversed(Base.metadata.sorted_tables):
            if "org_id" in table.c:
                s.execute(delete(table).where(table.c.org_id == org.id))
        s.execute(delete(Organisation).where(Organisation.id == org.id, Organisation.mode == "synthetic"))
    return live


def create_workspace(s, template_user, template_org):
    expected_email = os.getenv("GRD_DEMO_EMAIL", "demo@pharmapath.local").lower()
    if template_user.email != expected_email or template_user.role != "admin" or template_org.mode != "synthetic":
        d.fail("Isolated rehearsals are available only from the public synthetic evaluation account", 403)
    if os.getenv("GRD_PUBLIC_DEMO_WORKSPACES", "true").lower() != "true":
        d.fail("Private rehearsals are currently disabled", 409)
    opening = opening_snapshot()
    source = next((x for x in s.scalars(select(Dataset).where(Dataset.org_id == template_org.id))
                   if x.digest == opening["content_sha256"] and x.provenance.get("generator_version") == opening["generator_version"]), None)
    if not source or template_org.scenario_on != date.fromisoformat(opening["scenario_on"]):
        d.fail("The versioned dynamic scenario is not available; use the existing workspace", 409)
    if purge_expired(s, template_org) >= MAX_WORKSPACES:
        d.fail("Three rehearsals are already active. Rejoin one using its workspace email, or use the shared workspace until a slot expires.", 429)
    # Bound storage as well as the number of public demonstration sessions.
    if s.bind.dialect.name == "postgresql":
        from sqlalchemy import text
        if s.execute(text("SELECT pg_database_size(current_database())")).scalar() > 650_000_000:
            d.fail("Free database rehearsal capacity reached; use the existing shared workspace", 429)
    org = Organisation(name="Independent evaluation workspace", mode="synthetic", scenario_on=template_org.scenario_on)
    s.add(org)
    s.flush()
    prefix = org.id[:8]
    user = User(org_id=org.id, email=f"review.{prefix}@pharmapath.local", password_hash=template_user.password_hash,
                role="admin", location_ids=[])
    s.add(user)
    s.flush()
    locations = []
    for i, (label, kind, district, lat, lon) in enumerate([
        ("Guwahati central warehouse", "warehouse", "Kamrup Metropolitan", 26.145, 91.736),
        ("Guwahati distributor", "distributor", "Kamrup Metropolitan", 26.155, 91.745),
        ("Dibrugarh distributor", "distributor", "Dibrugarh", 27.4728, 94.912),
        ("Silchar distributor", "distributor", "Cachar", 24.833, 92.779),
        ("Jorhat distributor", "distributor", "Jorhat", 26.7509, 94.2037),
    ]):
        loc = Location(id=f"{prefix}-L{i}", org_id=org.id, name=label, kind=kind, district=district,
                       latitude=lat, longitude=lon, coordinate_source="Approximate town centre; fictional operating site")
        locations.append(loc)
        s.add(loc)
    s.flush()
    for a in locations:
        for b in locations:
            if a.id == b.id or b.kind == "warehouse":
                continue
            upper = (2 if b == locations[1] or b == locations[2] else 6 if b == locations[3] else 5) if a.kind == "warehouse" else 6
            s.add(Route(org_id=org.id, origin_id=a.id, destination_id=b.id, lead_days=max(1, upper - 2),
                        lead_days_upper=upper, min_shelf_days=30, safety_days=2, min_order=1,
                        cost_paise=5000, permitted=not (a == locations[2] and b == locations[3]),
                        policy_source="Illustrative rehearsal lanes; central-to-Dibrugarh two-day express assumption, not owner-confirmed"))
    from .dynamic_data import CATALOGUE, SITES
    product_map, site_map = {}, {}
    for sku, name, unit, pack, cost, _, _ in CATALOGUE:
        old = next((p for p in s.scalars(select(Product).where(Product.org_id == template_org.id))
                    if p.id.endswith("-D2-" + sku) and p.provenance.get("generator_version") == opening["generator_version"]), None)
        if old is None:
            d.fail("Dynamic product template is incomplete", 409)
        product = Product(id=f"{prefix}-D2-{sku}", org_id=org.id, name=name, base_unit=unit, pack_size=pack,
                          unit_cost_paise=cost, unit_conversions={"carton": pack}, transfer_allowed=old.transfer_allowed,
                          provenance={"evidence_type": "synthetic", "generator_version": opening["generator_version"],
                                      "scenario_priority": 3 if sku == "paracetamol" else 0,
                                      "review_start_location": locations[2].id if sku == "paracetamol" else None,
                                      "note": "Versioned generated data; illustrative express lane in this isolated rehearsal"})
        s.add(product)
        product_map[old.id] = product.id
    for i, loc in enumerate(locations):
        site_map[f"{template_org.id[:8]}-L{i}"] = loc.id
    dataset = Dataset(org_id=org.id, name=source.name, provenance=source.provenance,
                      digest=source.digest, row_count=source.row_count)
    s.add(dataset)
    s.flush()
    query = select(literal(prefix + "-") + Demand.id, literal(org.id), func.now(), Demand.date,
                   case(product_map, value=Demand.product_id), case(site_map, value=Demand.location_id),
                   Demand.quantity, Demand.measure, literal(dataset.id)).where(
                       Demand.org_id == template_org.id, Demand.dataset_id == source.id,
                       Demand.product_id.in_(product_map), Demand.location_id.in_(site_map))
    s.execute(insert(Demand).from_select(["id", "org_id", "created_at", "date", "product_id", "location_id", "quantity", "measure", "dataset_id"], query, include_defaults=False))
    copied = s.scalar(select(func.count()).select_from(Demand).where(Demand.org_id == org.id))
    if copied != source.row_count:
        raise ValueError("Incomplete rehearsal demand copy; transaction rolled back")
    products = {sku: f"{prefix}-D2-{sku}" for sku, *_ in CATALOGUE}
    for sku in products:
        for i, site in enumerate(SITES):
            lots = [x for x in opening["batches"] if x["product_code"] == sku and x["location_code"] == site]
            for lot in lots or [{"code": f"D2-{sku}-{site}-empty", "quantity": 0, "expiry": "2027-05-01"}]:
                batch = Batch(org_id=org.id, product_id=products[sku], location_id=locations[i].id,
                              code=lot["code"], expiry=date.fromisoformat(lot["expiry"]), quantity=0, reserved=0)
                s.add(batch)
                s.flush()
                d.change(s, user, batch, lot["quantity"], "isolated_synthetic_opening", dataset.id)
    mapping = {**product_map, **site_map, source.id: dataset.id}

    def remap(value):
        if isinstance(value, str):
            return mapping.get(value, value)
        if isinstance(value, list):
            return [remap(x) for x in value]
        if isinstance(value, dict):
            return {k: remap(v) for k, v in value.items()}
        return value

    copied_forecasts = set()
    for job in s.scalars(select(Job).where(Job.org_id == template_org.id, Job.kind == "forecast", Job.status == "completed").order_by(Job.created_at.desc())):
        pair = job.payload.get("product_id"), job.payload.get("location_id")
        if pair in copied_forecasts or pair[0] not in product_map or pair[1] not in site_map:
            continue
        if job.result.get("status") != "ready" or job.payload.get("as_of") != str(org.scenario_on):
            continue
        copied_forecasts.add(pair)
        s.add(Job(org_id=org.id, actor_id=user.id, kind="forecast", status="completed", progress=100,
                  payload=remap(job.payload), result={**remap(job.result), "same_dataset_cached_result": True}))
    expires = (now() + timedelta(hours=LIFETIME_HOURS)).isoformat()
    s.add(Workflow(org_id=org.id, kind=KIND, state="active", version=1, location_ids=[], identity=org.id,
                   payload={"origin_org_id": template_org.id, "disposable": True, "expires_at": expires,
                            "template": opening["generator_version"], "dataset_hash": source.digest}))
    d.audit(s, user, "demo.workspace_created", org.id, {"expires_at": expires, "copied_observations": copied})
    s.flush()
    return user, org

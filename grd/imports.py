import csv
from datetime import date
from typing import Annotated, Literal
import hashlib
import io
import zipfile
from itertools import islice

from pydantic import Field, ValidationError
from sqlalchemy import insert, select, tuple_

from . import domain as d
from .models import Dataset, Demand, Location, Product
from .schemas import Identifier, Input, Nonnegative

MAX_IMPORT_ROWS = 10_000
QUERY_BATCH_SIZE = 200


def chunks(values):
    for offset in range(0, len(values), QUERY_BATCH_SIZE):
        yield values[offset : offset + QUERY_BATCH_SIZE]


def catalogue(s, cls, user, identifiers):
    records = {}
    for group in chunks(list(identifiers)):
        records.update(
            (row.id, row)
            for row in s.scalars(select(cls).where(cls.org_id == user.org_id, cls.id.in_(group)))
        )
    return records


class Row(Input):
    date: date
    product_id: Identifier
    location_id: Identifier
    quantity: Nonnegative
    measure: str = Field(pattern="^(sales|requested)$")


class Provenance(Input):
    name: Annotated[str, Field(min_length=1, max_length=200)]
    source_url: Annotated[str, Field(min_length=1, max_length=2000)]
    licence: Annotated[str, Field(min_length=1, max_length=1000)]
    geography: Annotated[str, Field(min_length=1, max_length=200)]
    evidence_type: Literal["observed", "synthetic", "derived"]
    units: Annotated[str, Field(min_length=1, max_length=80)]
    limitations: Annotated[
        list[Annotated[str, Field(min_length=1, max_length=2000)]], Field(min_length=1, max_length=30)
    ]


def import_demand(s, user, org, raw, filename, metadata, dry_run):
    try:
        meta = Provenance.model_validate_json(metadata).model_dump()
        filename = filename.lower()
        if filename.endswith(".csv"):
            reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
            fields = reader.fieldnames or []
            if len(fields) != len(set(fields)):
                raise ValueError("Duplicate CSV column headers")
            data = list(islice(reader, MAX_IMPORT_ROWS + 1))
        elif filename.endswith(".xlsx"):
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                if sum(x.file_size for x in z.infolist()) > 30_000_000 or len(z.infolist()) > 200:
                    raise ValueError("Workbook expands beyond limit")
            import pandas as pd

            data = (
                pd.read_excel(io.BytesIO(raw), dtype=str, nrows=MAX_IMPORT_ROWS + 1)
                .fillna("")
                .to_dict("records")
            )
        else:
            raise ValueError("Use CSV or XLSX")
    except (ValueError, UnicodeError, zipfile.BadZipFile) as exc:
        d.fail(str(exc), 422)
    except Exception:
        # Malformed workbook internals are input errors, not server failures.
        d.fail("Cannot read this CSV/XLSX file; check its format and contents", 422)
    if not data:
        d.fail("The file contains no demand observations", 422)
    if len(data) > MAX_IMPORT_ROWS:
        d.fail("Maximum 10,000 rows per upload; split larger files", 413)
    errors, parsed, seen = [], [], set()
    for number, raw_row in enumerate(data, 2):
        try:
            # Reject decimal/fractional quantities before validating base units.
            raw_row["quantity"] = int(str(raw_row.get("quantity", "")))
            row = Row.model_validate(raw_row)
            d.scope(user, row.location_id)
            identity = (row.date, row.product_id, row.location_id, row.measure)
            if identity in seen:
                raise ValueError("Duplicate observation in file")
            seen.add(identity)
            parsed.append((number, row))
        except (ValueError, ValidationError) as exc:
            errors.append({"row": number, "error": str(exc)[:500]})
        except Exception as exc:
            if not hasattr(exc, "status_code"):
                raise
            errors.append({"row": number, "error": "Record or location not accessible"})

    # Batch catalogue reads and duplicate checks instead of repeating database
    # lookups for every observation in a large upload.
    products = catalogue(s, Product, user, {row.product_id for _, row in parsed})
    locations = catalogue(s, Location, user, {row.location_id for _, row in parsed})
    good = []
    for number, row in parsed:
        product = products.get(row.product_id)
        if product is None or row.location_id not in locations:
            errors.append({"row": number, "error": "Record or location not accessible"})
        elif meta["units"] not in [product.base_unit, "product_base_units"]:
            errors.append(
                {
                    "row": number,
                    "error": "Quantity units must match the product base unit; convert explicitly before import",
                }
            )
        else:
            good.append((number, row))
    digest = hashlib.sha256(raw).hexdigest()
    prior = s.scalar(select(Dataset).where(Dataset.org_id == user.org_id, Dataset.digest == digest))
    if prior:
        if prior.provenance != meta:
            d.fail("Identical file cannot be relabelled with different provenance")
        # A replay still checks the caller's current location scope and units.
        if not errors:
            return {"dataset_id": prior.id, "duplicate": True, "row_count": prior.row_count, "digest": digest}

    existing = set()
    identities = [(row.product_id, row.location_id, row.measure, row.date) for _, row in good]
    for group in chunks(identities):
        existing.update(
            tuple(row)
            for row in s.execute(
                select(Demand.product_id, Demand.location_id, Demand.measure, Demand.date).where(
                    Demand.org_id == user.org_id,
                    tuple_(Demand.product_id, Demand.location_id, Demand.measure, Demand.date).in_(group),
                )
            )
        )
    accepted = []
    for number, row in good:
        if (row.product_id, row.location_id, row.measure, row.date) in existing:
            errors.append(
                {
                    "row": number,
                    "error": "Observation already exists; corrections require a versioned replacement dataset",
                }
            )
        else:
            accepted.append(row)
    good = accepted
    errors.sort(key=lambda error: error["row"])
    result = {
        "digest": digest,
        "valid_rows": len(good),
        "invalid_rows": len(errors),
        "errors": errors[:100],
        "source_total": sum(x.quantity for x in good),
        "dry_run": dry_run,
        "provenance": meta,
    }
    if dry_run or errors:
        result["committed"] = False
        return result
    dataset = Dataset(
        org_id=user.org_id, name=meta["name"], provenance=meta, digest=digest, row_count=len(good)
    )
    s.add(dataset)
    s.flush()
    for group in chunks(good):
        s.execute(
            insert(Demand),
            [{"org_id": user.org_id, "dataset_id": dataset.id, **row.model_dump()} for row in group],
        )
    org.revision += 1
    d.audit(
        s,
        user,
        "dataset.imported",
        dataset.id,
        {"digest": digest, "rows": len(good), "total": result["source_total"]},
        sorted({x.location_id for x in good}),
    )
    return {**result, "dataset_id": dataset.id, "committed": True}

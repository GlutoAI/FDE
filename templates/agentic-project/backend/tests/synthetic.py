"""Synthetic records, documents, and import directories for tests; tests never read ``data/``.

Two tenants share record ID ``REC-1001`` on purpose, so every isolation test can check that a
lookup by key alone never crosses tenants.
"""

import asyncio
import csv
import hashlib
import json
from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.context import TenantScope
from app.db.engine import build_database_url, open_database
from app.db.records import ExampleRecord

ALPHA = TenantScope(tenant_id="tenant_alpha")
BETA = TenantScope(tenant_id="tenant_beta")
UPDATED_AT = datetime(2026, 9, 20, 12, tzinfo=UTC)
RECORDS_FILE = "example_records.csv"


def run_with_engine(tmp_path: Path, scenario: Callable[[AsyncEngine], Awaitable[None]]) -> None:
    """Run an async scenario against a fresh SQLite database in ``tmp_path``."""

    async def run_scenario() -> None:
        async with open_database(build_database_url(tmp_path, None)) as engine:
            await scenario(engine)

    asyncio.run(run_scenario())


def build_record(
    record_id: str = "REC-1001", tenant_id: str = "tenant_alpha", **changes: object
) -> ExampleRecord:
    """Return a valid closed example record; ``changes`` override individual fields."""
    values: dict[str, object] = {
        "tenant_id": tenant_id,
        "record_id": record_id,
        "owner_id": "user-1",
        "name": "Harbor Cafe",
        "category": "meals",
        "amount_cents": 4_250,
        "currency": "USD",
        "opened_on": date(2026, 9, 2),
        "closed_on": date(2026, 9, 3),
        "updated_at": UPDATED_AT,
    }
    return ExampleRecord.model_validate(values | changes)


# REC-1002 is still open; tenant_beta reuses the ID REC-1001.
SYNTHETIC_RECORDS = (
    build_record("REC-1001"),
    build_record("REC-1002", closed_on=None),
    build_record(
        "REC-1003",
        name="Northwind Air",
        category="travel",
        amount_cents=38_900,
        opened_on=date(2026, 9, 10),
        closed_on=date(2026, 9, 11),
    ),
    build_record("REC-1001", "tenant_beta", name="Summit Supplies", closed_on=None),
)

SYNTHETIC_PREFERENCES = (
    {
        "tenant_id": "tenant_alpha",
        "preference_id": "pref_tone",
        "record_id": None,
        "key": "summary_tone",
        "value": "Plain and brief.",
        "approved_by": "user-1",
        "status": "approved",
        "source": "settings_page",
        "created_at": "2026-09-15T00:00:00Z",
        "expires_at": "2027-09-01T00:00:00Z",
    },
    {
        "tenant_id": "tenant_alpha",
        "preference_id": "pref_report",
        "record_id": None,
        "key": "report_day",
        "value": "Monday",
        "approved_by": "user-1",
        "status": "approved",
        "source": "settings_page",
        "created_at": "2026-09-15T00:00:00Z",
        "expires_at": None,
    },
    {
        "tenant_id": "tenant_alpha",
        "preference_id": "pref_rec_1002",
        "record_id": "REC-1002",
        "key": "reviewer_note",
        "value": "Waiting on the owner to confirm the amount.",
        "approved_by": "user-2",
        "status": "approved",
        "source": "review_comment",
        "created_at": "2026-09-16T00:00:00Z",
        "expires_at": None,
    },
)

ALPHA_POLICY = (
    "Records of 25 dollars or more need a supporting document.\n\n"
    "Meals with clients are allowed up to 75 dollars per person.\n\n"
    "Submitting the same record twice is a duplicate and must be withdrawn."
)
BETA_POLICY = "Office supplies above 200 dollars need manager approval before purchase."


def write_records_csv(path: Path, records: Sequence[ExampleRecord]) -> Path:
    """Write records as the CSV an export would produce: None becomes an empty cell."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(ExampleRecord.model_fields))
        writer.writeheader()
        for record in records:
            row = record.model_dump(mode="json")
            writer.writerow({key: "" if value is None else value for key, value in row.items()})
    return path


def write_record_import(directory: Path, *, has_preferences: bool = True) -> Path:
    """Write a complete structured import directory, optionally with ``preferences.json``."""
    write_records_csv(directory / RECORDS_FILE, SYNTHETIC_RECORDS)
    if has_preferences:
        (directory / "preferences.json").write_text(json.dumps(list(SYNTHETIC_PREFERENCES)))
    return directory


def build_document_entry(
    document_id: str, tenant_id: str, path: str, content: bytes
) -> dict[str, object]:
    """Return one ``index.json`` entry whose hash matches ``content``."""
    return {
        "document_id": document_id,
        "tenant_id": tenant_id,
        "document_type": "policy",
        "title": f"Policy for {tenant_id}",
        "path": path,
        "effective_date": "2026-01-01",
        "version": 1,
        "sha256": hashlib.sha256(content).hexdigest(),
        "trust_level": "untrusted_content",
    }


def write_document_import(directory: Path) -> Path:
    """Write a two-tenant document directory: one policy per tenant, plus ``index.json``."""
    entries = []
    for document_id, tenant_id, text in (
        ("policy-alpha", "tenant_alpha", ALPHA_POLICY),
        ("policy-beta", "tenant_beta", BETA_POLICY),
    ):
        path = f"{tenant_id}/policy.md"
        content = text.encode()
        (directory / tenant_id).mkdir(parents=True, exist_ok=True)
        (directory / path).write_bytes(content)
        entries.append(build_document_entry(document_id, tenant_id, path, content))
    (directory / "index.json").write_text(json.dumps(entries))
    return directory

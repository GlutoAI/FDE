"""Synthetic import directories written into ``tmp_path``; tests never read ``data/``."""

import csv
import hashlib
import json
from collections.abc import Sequence
from datetime import UTC, date, datetime
from pathlib import Path

from app.core.context import TenantScope
from app.db.records import ExpenseRecord

ALPHA = TenantScope(tenant_id="tenant_alpha")
BETA = TenantScope(tenant_id="tenant_beta")
UPDATED_AT = datetime(2026, 9, 20, 12, tzinfo=UTC)


def build_expense(
    expense_id: str = "EXP-1001", tenant_id: str = "tenant_alpha", **changes: object
) -> ExpenseRecord:
    values: dict[str, object] = {
        "tenant_id": tenant_id,
        "expense_id": expense_id,
        "submitted_by": "user-1",
        "merchant": "Harbor Cafe",
        "expense_date": date(2026, 9, 2),
        "posted_date": date(2026, 9, 3),
        "amount_cents": 4_250,
        "currency": "USD",
        "category": "meals",
        "receipt_id": f"RCT-{expense_id}",
        "updated_at": UPDATED_AT,
    }
    return ExpenseRecord.model_validate(values | changes)


# EXP-1002 repeats EXP-1001 without a receipt; tenant_beta reuses the ID EXP-1001.
SYNTHETIC_EXPENSES = (
    build_expense("EXP-1001"),
    build_expense("EXP-1002", receipt_id=None),
    build_expense(
        "EXP-1003",
        merchant="Northwind Air",
        expense_date=date(2026, 9, 10),
        posted_date=date(2026, 9, 11),
        amount_cents=38_900,
        category="travel",
    ),
    build_expense("EXP-1001", "tenant_beta", merchant="Summit Supplies", receipt_id=None),
)

SYNTHETIC_PREFERENCES = (
    {
        "tenant_id": "tenant_alpha",
        "preference_id": "pref_tone",
        "expense_id": None,
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
        "expense_id": None,
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
        "preference_id": "pref_exp_1002",
        "expense_id": "EXP-1002",
        "key": "reviewer_note",
        "value": "Team lunch; receipt requested from the submitter.",
        "approved_by": "user-2",
        "status": "approved",
        "source": "review_comment",
        "created_at": "2026-09-16T00:00:00Z",
        "expires_at": None,
    },
)

ALPHA_POLICY = (
    "Receipts are required for every expense of 25 dollars or more.\n\n"
    "Meals with clients are reimbursable up to 75 dollars per person.\n\n"
    "Submitting the same expense twice is a duplicate and must be withdrawn."
)
BETA_POLICY = "Office supplies above 200 dollars need manager approval before purchase."


def write_expense_csv(path: Path, records: Sequence[ExpenseRecord]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(ExpenseRecord.model_fields))
        writer.writeheader()
        for record in records:
            row = record.model_dump(mode="json")
            writer.writerow({key: "" if value is None else value for key, value in row.items()})
    return path


def write_expense_import(directory: Path, *, has_preferences: bool = True) -> Path:
    write_expense_csv(directory / "expenses.csv", SYNTHETIC_EXPENSES)
    if has_preferences:
        (directory / "preferences.json").write_text(json.dumps(list(SYNTHETIC_PREFERENCES)))
    return directory


def build_document_entry(
    document_id: str, tenant_id: str, path: str, content: bytes
) -> dict[str, object]:
    return {
        "document_id": document_id,
        "tenant_id": tenant_id,
        "document_type": "policy",
        "title": f"Expense policy for {tenant_id}",
        "path": path,
        "effective_date": "2026-01-01",
        "version": 1,
        "sha256": hashlib.sha256(content).hexdigest(),
        "trust_level": "untrusted_content",
    }


def write_document_import(directory: Path) -> Path:
    entries = []
    for document_id, tenant_id, text in (
        ("policy-alpha", "tenant_alpha", ALPHA_POLICY),
        ("policy-beta", "tenant_beta", BETA_POLICY),
    ):
        path = f"{tenant_id}/expense-policy.md"
        content = text.encode()
        (directory / tenant_id).mkdir(parents=True, exist_ok=True)
        (directory / path).write_bytes(content)
        entries.append(build_document_entry(document_id, tenant_id, path, content))
    (directory / "index.json").write_text(json.dumps(entries))
    return directory

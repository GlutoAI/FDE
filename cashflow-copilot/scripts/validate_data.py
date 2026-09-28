#!/usr/bin/env python3
"""Check fixture integrity and independently recompute the golden cash-flow result."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
ERRORS = []
CHECKS = 0


def check(condition, message):
    global CHECKS
    CHECKS += 1
    if not condition:
        ERRORS.append(message)


def read(relative):
    return json.loads((DATA / relative).read_text(encoding="utf-8"))


def timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def validate():
    config = read("dataset_config.json")
    manifest = read("manifest.json")
    as_of = timestamp(config["as_of"])
    today = as_of.date().isoformat()
    tenant = config["primary_tenant_id"]
    horizon = config["forecast_end_inclusive"]
    expected_files = {entry["path"] for entry in manifest["files"]}
    check(len(expected_files) == len(manifest["files"]), "Manifest has duplicate paths")
    actual_files = {p.relative_to(DATA).as_posix() for p in DATA.rglob("*") if p.is_file()}
    check(actual_files == expected_files | {"manifest.json"}, "Manifest file inventory differs from disk")
    for entry in manifest["files"]:
        raw = (DATA / entry["path"]).read_bytes()
        check(hashlib.sha256(raw).hexdigest() == entry["sha256"], "Checksum mismatch: " + entry["path"])
        check(len(raw) == entry["bytes"], "File size mismatch: " + entry["path"])
    tables = {}
    keys = {
        "tenants": "tenant_id", "users": "user_id", "memberships": "membership_id",
        "connections": "connection_id", "preferences": "preference_id", "customers": "customer_id",
        "vendors": "vendor_id", "invoices": "invoice_id", "payments": "payment_id",
        "disputes": "dispute_id", "bills": "bill_id", "payroll": "payroll_id",
        "bank_accounts": "bank_account_id", "bank_transactions": "bank_transaction_id",
        "receipt_assumptions": "assumption_id",
    }
    for folder in ("structured", "identity", "memory"):
        for path in sorted((DATA / folder).glob("*.json")):
            name = path.stem
            if name not in keys:
                continue
            rows = read(path.relative_to(DATA))
            tables[name] = {r[keys[name]]: r for r in rows}
            check(len(tables[name]) == len(rows), "Duplicate primary keys in " + name)
            check(len(rows) == manifest["table_row_counts"][name], "Manifest row count: " + name)
            csv_path = path.with_suffix(".csv")
            if folder == "structured":
                with csv_path.open(newline="", encoding="utf-8") as stream:
                    csv_rows = list(csv.DictReader(stream))
                expected = [{k: "" if v is None else str(v).lower() if isinstance(v, bool) else str(v)
                             for k, v in r.items()} for r in rows]
                check(csv_rows == expected, "CSV/JSON mismatch in " + name)
    check(set(tables) == set(keys), "Missing or extra normalized table")
    documents = read("documents/index.json")
    docs = {d["document_id"]: d for d in documents}
    check(len(docs) == len(documents) == manifest["document_count"], "Document ID/count mismatch")

    def reference(record, target, field, nullable=False):
        key = record.get(field)
        if nullable and key is None:
            return
        found = target.get(key)
        check(found is not None, "Missing {} reference: {}".format(field, key))
        if found is not None and "tenant_id" in record and "tenant_id" in found:
            check(record["tenant_id"] == found["tenant_id"], "Cross-tenant reference: {}".format(key))

    for name, records in tables.items():
        for record in records.values():
            if name not in ("users", "tenants"):
                reference(record, tables["tenants"], "tenant_id")
            for field, value in record.items():
                if field.endswith("_cents"):
                    check(type(value) is int, "Money must be integer cents: {}.{}".format(name, field))
                    if name != "bank_transactions":
                        check(value >= 0, "Unexpected negative monetary value: {}.{}".format(name, field))
                if field == "currency":
                    check(value == "USD", "Unsupported fixture currency")
                if field.endswith("_date") and value:
                    date.fromisoformat(value)
                if field.endswith("_at") and value:
                    moment = timestamp(value)
                    if field != "expires_at":
                        check(moment <= as_of, "Future fact in baseline: {}.{}".format(name, field))
                if field.endswith("email"):
                    check(value.split("@")[-1].endswith(".example"), "Non-reserved email domain")
            for field, target in [("customer_id", "customers"), ("vendor_id", "vendors"),
                                  ("invoice_id", "invoices"), ("bank_account_id", "bank_accounts"),
                                  ("user_id", "users"), ("approved_by", "users")]:
                if field in record and keys[name] != field:
                    reference(record, tables[target], field, nullable=True)
            if "evidence_document_id" in record:
                reference(record, docs, "evidence_document_id")
    for membership in tables["memberships"].values():
        check(membership["role"] in read("identity/role_permissions.json"), "Unknown role")
    for pref in tables["preferences"].values():
        check(any(m["user_id"] == pref["approved_by"] and m["tenant_id"] == pref["tenant_id"]
                  and m["role"] == "owner" and m["active"] for m in tables["memberships"].values()),
              "Preference approver is not a tenant owner")

    for doc in documents:
        reference(doc, tables["tenants"], "tenant_id")
        reference(doc, tables["customers"], "customer_id", nullable=True)
        reference(doc, tables["invoices"], "invoice_id", nullable=True)
        reference(doc, docs, "amends_document_id", nullable=True)
        path = DATA / doc["path"]
        check(path.is_relative_to(DATA / "documents"), "RAG document outside documents directory")
        content = path.read_bytes()
        check(hashlib.sha256(content).hexdigest() == doc["sha256"], "Document hash mismatch")
        check(doc["effective_date"] <= today, "Future document leaked into baseline")
        check(doc["trust_level"] == "untrusted_content", "Documents must not be instructions to the model")
        if doc["invoice_id"]:
            inv = tables["invoices"][doc["invoice_id"]]
            check(inv["customer_id"] == doc["customer_id"], "Document/invoice customer mismatch")
    check(docs["amendment-silverline-net45"]["amends_document_id"] == "contract-a-006", "Missing contract precedence")

    for inv in tables["invoices"].values():
        payments = [p for p in tables["payments"].values() if p["invoice_id"] == inv["invoice_id"]]
        paid = sum(p["amount_cents"] for p in payments)
        check(inv["total_cents"] == inv["subtotal_cents"] + inv["tax_cents"], "Invoice total mismatch")
        check(paid == inv["paid_cents"], "Payment reconciliation failed: " + inv["invoice_id"])
        check(inv["balance_cents"] == inv["total_cents"] - paid, "Invoice balance mismatch")
        check(inv["issue_date"] <= today and inv["issue_date"] <= inv["due_date"], "Invoice dates inconsistent")
        check(inv["disputed_cents"] <= inv["balance_cents"], "Dispute exceeds open balance")
        disputes = [d for d in tables["disputes"].values() if d["invoice_id"] == inv["invoice_id"] and d["status"] == "open"]
        check(sum(d["disputed_cents"] for d in disputes) == inv["disputed_cents"], "Dispute balance mismatch")
        status = "paid" if inv["balance_cents"] == 0 else "disputed" if disputes else "partially_paid" if paid else "open"
        check(inv["status"] == status, "Invoice status mismatch")
        for p in payments:
            check(inv["issue_date"] <= p["payment_date"] <= today, "Payment outside baseline invoice dates")
            check(p["customer_id"] == inv["customer_id"], "Payment/invoice customer mismatch")
            check(p["status"] == "settled" and p["amount_cents"] > 0, "Invalid settlement")
    for d in tables["disputes"].values():
        check(tables["invoices"][d["invoice_id"]]["issue_date"] <= d["opened_date"] <= today, "Invalid dispute date")

    bank_rows = list(tables["bank_transactions"].values())
    movement_refs = Counter((r["kind"], r["reference_id"]) for r in bank_rows)
    for p in tables["payments"].values():
        check(movement_refs[("customer_payment", p["payment_id"])] == 1, "Payment missing/duplicated in bank ledger")
    for bill in tables["bills"].values():
        check(bill["total_cents"] - bill["paid_cents"] == bill["balance_cents"], "Bill amount mismatch")
        check(bill["issue_date"] <= today and bill["issue_date"] <= bill["due_date"], "Invalid bill dates")
        paid = bill["status"] == "paid"
        check(movement_refs[("bill_payment", bill["bill_id"])] == int(paid), "Bill movement mismatch")
        check((paid and bill["balance_cents"] == 0 and bill["paid_date"] <= today) or
              (not paid and bill["paid_cents"] == 0 and bill["scheduled_payment_date"] > today), "Invalid bill state")
    for payroll in tables["payroll"].values():
        paid = payroll["status"] == "paid"
        check(movement_refs[("payroll_payment", payroll["payroll_id"])] == int(paid), "Payroll movement mismatch")
        check((payroll["pay_date"] <= today) == paid, "Payroll date/status mismatch")
    lookup = {"customer_payment": ("payments", "amount_cents", "payment_date", 1),
              "bill_payment": ("bills", "paid_cents", "paid_date", -1),
              "payroll_payment": ("payroll", "total_cash_requirement_cents", "pay_date", -1)}
    for bank in bank_rows:
        check(bank["posted_date"] <= today, "Future bank movement leaked into baseline")
        if bank["kind"] in lookup:
            table, amount_field, date_field, sign = lookup[bank["kind"]]
            reference(bank, tables[table], "reference_id")
            source = tables[table][bank["reference_id"]]
            check(bank["amount_cents"] == sign * source[amount_field], "Bank/source amount mismatch")
            check(bank["posted_date"] == source[date_field], "Bank/source date mismatch")
        else:
            check(bank["kind"] == "opening_balance", "Unknown bank movement kind")
    for account in tables["bank_accounts"].values():
        entries = [b for b in bank_rows if b["bank_account_id"] == account["bank_account_id"]]
        check(sum(b["kind"] == "opening_balance" for b in entries) == 1, "Expected one opening balance")
        check(sum(b["amount_cents"] for b in entries) == account["balance_cents"], "Bank balance does not reconcile")
        running = 0
        for entry in sorted(entries, key=lambda b: (b["posted_date"], b["bank_transaction_id"])):
            running += entry["amount_cents"]
            check(running >= 0, "Historical ledger has an unmodeled overdraft")
    for receipt in tables["receipt_assumptions"].values():
        inv = tables["invoices"][receipt["invoice_id"]]
        check(0 < receipt["amount_cents"] <= inv["balance_cents"], "Invalid expected receipt")
        check(receipt["expected_date"] > today, "Receipt assumption must refer to future cash")
        check(receipt["include_in_baseline"] == (receipt["evidence_status"] == "scheduled_by_customer"), "Tentative receipt included")

    oracle = read("evaluation/expected_cashflow.json")
    opening = sum(b["balance_cents"] for b in tables["bank_accounts"].values() if b["tenant_id"] == tenant)
    receipts = [r for r in tables["receipt_assumptions"].values()
                if r["tenant_id"] == tenant and r["include_in_baseline"] and today < r["expected_date"] <= horizon]
    bills = [b for b in tables["bills"].values() if b["tenant_id"] == tenant and
             b["scheduled_payment_date"] and today < b["scheduled_payment_date"] <= horizon]
    payroll = [p for p in tables["payroll"].values() if p["tenant_id"] == tenant and
               p["status"] == "scheduled" and today < p["pay_date"] <= horizon]
    receipt_total = sum(r["amount_cents"] for r in receipts)
    bill_total = sum(b["balance_cents"] for b in bills)
    payroll_total = sum(p["total_cash_requirement_cents"] for p in payroll)
    closing = opening + receipt_total - bill_total - payroll_total
    for key, result in [("starting_cash_cents", opening), ("baseline_receipts_cents", receipt_total),
                        ("scheduled_bills_cents", bill_total), ("scheduled_payroll_cents", payroll_total),
                        ("baseline_closing_cash_cents", closing)]:
        check(result == oracle[key], "Cash-flow oracle mismatch: " + key)
    check(closing == -800000, "Golden scenario must have an $8,000 baseline shortfall")
    overdue = [i for i in tables["invoices"].values() if i["tenant_id"] == tenant
               and i["balance_cents"] > 0 and i["due_date"] < today]
    held = {d["invoice_id"] for d in tables["disputes"].values()
            if d["tenant_id"] == tenant and d["status"] == "open" and d["collection_hold"]}
    eligible = [i for i in overdue if i["invoice_id"] not in held]
    check(sorted(i["invoice_id"] for i in overdue) == oracle["overdue_invoice_ids"], "Overdue oracle mismatch")
    check(sorted(i["invoice_id"] for i in eligible) == oracle["eligible_reminder_invoice_ids"], "Eligibility oracle mismatch")
    check(sorted(held) == oracle["held_invoice_ids"], "Held-invoice oracle mismatch")
    check(sum(i["balance_cents"] for i in overdue) == oracle["overdue_balance_cents"], "Overdue total mismatch")
    eligible_total = sum(i["balance_cents"] for i in eligible)
    check(eligible_total == oracle["eligible_collection_balance_cents"], "Eligible total mismatch")
    check(closing + eligible_total == oracle["scenario_if_both_eligible_balances_settle_before_payroll_cents"], "Collection scenario mismatch")
    check(closing + tables["invoices"]["INV-A-1001"]["balance_cents"] == oracle["scenario_if_harbor_only_settles_before_payroll_cents"], "Harbor scenario mismatch")
    tentative = sum(r["amount_cents"] for r in tables["receipt_assumptions"].values()
                    if r["tenant_id"] == tenant and r["evidence_status"] == "tentative")
    check(closing + tentative == oracle["scenario_if_only_tentative_summit_installment_settles_cents"], "Tentative scenario mismatch")
    expected_days = [(date.fromisoformat(today) + timedelta(days=i)).isoformat() for i in range(1, 15)]
    check([d["date"] for d in oracle["daily_projection"]] == expected_days, "Daily forecast has missing or duplicate dates")
    daily_balances = []
    for point in oracle["daily_projection"]:
        day = point["date"]
        daily_receipts = sum(r["amount_cents"] for r in receipts if r["expected_date"] == day)
        daily_bills = sum(b["balance_cents"] for b in bills if b["scheduled_payment_date"] == day)
        daily_payroll = sum(p["total_cash_requirement_cents"] for p in payroll if p["pay_date"] == day)
        recomputed = opening + sum(r["amount_cents"] for r in receipts if r["expected_date"] <= day)
        recomputed -= sum(b["balance_cents"] for b in bills if b["scheduled_payment_date"] <= day)
        recomputed -= sum(p["total_cash_requirement_cents"] for p in payroll if p["pay_date"] <= day)
        check((daily_receipts, daily_bills, daily_payroll, recomputed) ==
              (point["receipts_cents"], point["bills_cents"], point["payroll_cents"], point["closing_cash_cents"]),
              "Daily cash-flow mismatch on " + day)
        daily_balances.append((day, recomputed))
    check(min(v for _, v in daily_balances) == oracle["minimum_cash_cents"], "Minimum cash mismatch")
    check(next(day for day, v in daily_balances if v < 0) == oracle["first_negative_cash_date"], "Shortfall date mismatch")

    for draft in read("workflow/drafts.json"):
        reference(draft, tables["invoices"], "invoice_id")
        for doc_id in draft["evidence_document_ids"]:
            reference(dict(tenant_id=draft["tenant_id"], evidence_document_id=doc_id), docs, "evidence_document_id")
        check(draft["status"] == "pending_approval" and draft["approval_id"] is None, "Baseline draft cannot be approved")
    check(read("workflow/approvals.json") == [], "Baseline contains unexpected approval")
    check(read("workflow/action_log.json") == [], "Baseline contains unexpected external action")
    cases = [json.loads(line) for line in (DATA / "evaluation/cases.jsonl").read_text().splitlines()]
    check(len(cases) == manifest["evaluation_case_count"], "Evaluation count mismatch")
    check(len({c["case_id"] for c in cases}) == len(cases), "Duplicate evaluation IDs")
    for case in cases:
        reference(case, tables["users"], "user_id")
        reference(case, tables["tenants"], "tenant_id")
        check(case["split"] in ("regression", "holdout"), "Unknown evaluation split")
        for doc_id in case["relevant_document_ids"]:
            reference(dict(tenant_id=case["tenant_id"], evidence_document_id=doc_id), docs, "evidence_document_id")
        if case["scenario_fixture"]:
            scenario = read(case["scenario_fixture"])
            check(scenario["tenant_id"] == case["tenant_id"], "Scenario tenant mismatch")
            check(scenario["apply_to"] == "isolated_copy_of_baseline", "Scenario must not mutate baseline")
    scenarios = list((DATA / "evaluation/scenarios").glob("*.json"))
    check(len(scenarios) == manifest["scenario_count"], "Scenario count mismatch")
    for path in scenarios:
        scenario = read(path.relative_to(DATA))
        for event in scenario.get("events", []):
            check(timestamp(event["occurred_at"]) > as_of, "Scenario event is not after baseline")
            check(event["payment_id"] not in tables["payments"], "Future scenario payment leaked into baseline")
    primary_names = {c["display_name"] for c in tables["customers"].values() if c["tenant_id"] == tenant}
    other_names = {c["display_name"] for c in tables["customers"].values() if c["tenant_id"] != tenant}
    check(len(primary_names & other_names) == 3, "Missing tenant-isolation name collisions")

    if ERRORS:
        print("FAILED: {} errors across {} checks".format(len(ERRORS), CHECKS))
        for error in ERRORS:
            print(" - " + error)
        raise SystemExit(1)
    print("PASS: {} integrity checks; {} tables, {} documents, {} evaluation cases.".format(
        CHECKS, len(tables), len(documents), len(cases)))
    print("Aurora: $42,000 cash + $12,000 scheduled receipts - $22,000 bills - $40,000 payroll = -$8,000.")
    print("All payments and bank balances reconcile; tenant references and file hashes are consistent.")


if __name__ == "__main__":
    try:
        validate()
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as error:
        print("FAILED: malformed or missing fixture: {}".format(error))
        raise SystemExit(1)

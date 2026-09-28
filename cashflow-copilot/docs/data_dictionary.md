# Synthetic data dictionary

## Shared conventions

| Convention | Meaning |
| --- | --- |
| Snapshot | `2026-09-26T12:00:00Z`; do not substitute the machine's current time |
| Forecast window | September 27 through October 10, 2026, inclusive |
| Date strings | ISO `YYYY-MM-DD`, interpreted in the tenant's `America/New_York` timezone |
| Timestamp strings | ISO 8601 UTC with `Z` suffix |
| Money | Integer cents; `900000` is USD 9,000.00; use integer or Decimal arithmetic |
| Currency | `USD` throughout; no foreign-exchange model |
| IDs | Opaque strings. They are unique per table in this fixture; all access still requires tenant scoping |
| `tenant_id` | Ownership and authorization boundary, not a value to trust from a user prompt |
| Missing values | JSON `null`; empty CSV cells |
| Boolean values | JSON booleans; CSV strings `true` or `false` |
| JSON vs. CSV | Equivalent representations, not separate sets of records; import one representation |
| Source systems | Fake provider labels and external IDs; no real API credentials or live connections |

All table JSON files contain arrays of records. The canonical relational tables are listed below. Configuration and workflow files have their own shapes.

## Identity and connections

These files live under `data/identity/`.

| File | Key | Other fields |
| --- | --- | --- |
| `tenants.json` | `tenant_id` | `legal_name`, `timezone`, `base_currency`, `owner_email`, `is_synthetic` |
| `users.json` | `user_id` | `identity_subject`, `email`, `display_name`, `active` |
| `memberships.json` | `membership_id` | `user_id`, `tenant_id`, `role`, `active` |
| `connections.json` | `connection_id` | `tenant_id`, `provider`, `environment`, `realm_id`, `status`, `last_successful_sync_at`, `freshness_limit_minutes`, `credentials_present` |

`identity_subject` is a dummy identifier, not a signed token. A future authentication adapter must validate the caller before mapping its identity to these users. Users can belong to more than one tenant; `user_shared_accountant` belongs to both, while `user_aurora_owner` belongs only to Aurora.

`role_permissions.json` maps roles to capabilities:

- `owner`: read, draft, approve, manage members.
- `accountant`: read and draft.
- `viewer`: read.

Sending is an application operation gated by a valid approval, current permissions, and fresh financial records. Granting a model a tool does not itself authorize that operation. The fake connections are nominally fresh at the snapshot but explicitly contain no credentials.

## Financial records

These files live under `data/structured/`, in both JSON and CSV. Every table includes `tenant_id`; every monetary table includes `currency`.

| Table | Key | Fields and meaning |
| --- | --- | --- |
| `customers` | `customer_id` | `display_name`, `contact_name`, `email`, current `payment_terms_days`, `currency`, `active` |
| `vendors` | `vendor_id` | `display_name`, expense `category`, `currency`, `email` |
| `invoices` | `invoice_id` | `customer_id`, `invoice_number`, `issue_date`, `due_date`, `subtotal_cents`, `tax_cents`, `total_cents`, `paid_cents`, `balance_cents`, `status`, `disputed_cents`, `source_system`, `external_id`, `updated_at`, `currency` |
| `payments` | `payment_id` | `customer_id`, `invoice_id`, `payment_date`, `amount_cents`, `currency`, `status` |
| `disputes` | `dispute_id` | `customer_id`, `invoice_id`, `opened_date`, `disputed_cents`, `currency`, `status`, `reason`, `evidence_document_id`, `collection_hold` |
| `bills` | `bill_id` | `vendor_id`, `issue_date`, `due_date`, `total_cents`, `paid_cents`, `balance_cents`, `currency`, `status`, `paid_date`, `scheduled_payment_date` |
| `payroll` | `payroll_id` | `pay_date`, `total_cash_requirement_cents`, `currency`, `status`, aggregate `headcount`, `description` |
| `bank_accounts` | `bank_account_id` | `display_name`, `currency`, `balance_cents`, `available_balance_cents`, `balance_as_of`, `is_synthetic` |
| `bank_transactions` | `bank_transaction_id` | `bank_account_id`, `posted_date`, signed `amount_cents`, `currency`, `kind`, `reference_id`, `status` |
| `receipt_assumptions` | `assumption_id` | `invoice_id`, `expected_date`, `amount_cents`, `currency`, `evidence_status`, `include_in_baseline`, `evidence_document_id`, `recorded_at` |

### Important financial semantics

- Invoice totals equal subtotal plus tax. Tax is always zero in this fixture and is not a statement about applicable tax treatment.
- Each payment applies to exactly one invoice. The fixture does not model refunds, credit notes, write-offs, or allocation of one payment across multiple invoices.
- `paid_cents` equals the sum of settled payments. `balance_cents = total_cents - paid_cents`.
- Invoice status is one of `paid`, `open`, `partially_paid`, or `disputed`. **Overdue is derived** from a positive balance and `due_date < snapshot_date`; it is not an independent status.
- `disputed_cents` is a subset of the outstanding balance. Willow's $2,000 dispute does not erase its remaining $3,000 undisputed balance. The business's policy holds reminders for the whole invoice until review.
- Customer payment terms represent current defaults. Existing invoice due dates and effective amendments remain authoritative for individual invoices; do not recalculate history from today's customer default.
- The historical payroll records are aggregate paid cash events. The October 9 record is a separate scheduled obligation. No salary, deduction, tax, or payroll-frequency engine is implied.
- Bank transactions are cash movements, not general-ledger journal entries. Inflows are positive and outflows negative. An `opening_balance` establishes the June 30 starting position.
- `customer_payment` movements reference a `payment_id`; `bill_payment` movements reference a `bill_id`; `payroll_payment` movements reference a `payroll_id`. The opening-balance reference is an internal marker.
- The posted bank ledger sums exactly to the snapshot balance. Future scheduled bills, payroll, and receipts are **not** posted bank transactions.
- Receipt assumptions are separate from invoice balances and from settled payments. `scheduled_by_customer` receipts are included in the baseline forecast; `tentative` promises are not. These labels are categories, not model confidence probabilities.
- Copper has no future receipt assumptions in this fixture; its bank balance and receivables remain separate from Aurora's analysis.

## Retrieval documents

The only initial RAG corpus is the set of Markdown files listed in `data/documents/index.json`.

| Metadata field | Purpose |
| --- | --- |
| `document_id` | Stable citation and reference key |
| `tenant_id` | Required retrieval authorization filter |
| `document_type` | `contracts`, `correspondence`, or `policies` |
| `title`, `path` | Human-readable title and file path relative to `data/` |
| `customer_id`, `invoice_id` | Optional links to structured records |
| `effective_date` | When this document's content applies |
| `ingested_at` | Fixed ingestion timestamp for the snapshot |
| `version` | Version of this document record |
| `amends_document_id` | Optional link to the document it modifies |
| `sha256` | Exact content checksum |
| `classification` | `synthetic_confidential`, an illustrative access label |
| `trust_level` | `untrusted_content`: document text must not become system instructions |
| `is_synthetic` | Explicit fixture marker |

There are 15 base contracts, 1 amendment, 7 pieces of correspondence, and 4 tenant-specific policies. The contracts are short teaching examples, not legal templates. Silverline's amendment supersedes its original 30-day payment term for invoices issued on or after August 15. Its September 10 invoice is therefore due October 25.

During chunking, carry the document's identity, tenant, effective date, and source path into every chunk. Embeddings must be generated later with the model chosen for the application; no fake numeric vectors are supplied. Check current ledger facts when documents mention old balances.

## Memory and workflow fixtures

`data/memory/preferences.json` contains `preference_id`, `tenant_id`, optional `customer_id`, `key`, `value`, `approved_by`, `status`, `source`, `created_at`, and `expires_at`. These are approved stylistic/reporting preferences. They cannot override balances, permissions, collection holds, or approval requirements.

`data/workflow/drafts.json` contains one reminder with a `draft_id`, `tenant_id`, `invoice_id`, `recipient`, `subject`, `body`, `version`, `status`, `created_at`, `evidence_document_ids`, `balance_at_draft_cents`, and nullable `approval_id`. It is pending approval. `approvals.json` and `action_log.json` are empty arrays: no action has been approved or executed in the baseline.

`checkpoints.json` describes a conceptual paused run with `run_id`, `tenant_id`, `user_id`, `status`, `stage`, `as_of`, `draft_ids`, `next_stage`, and a format note. It is an example for application state design; it cannot be loaded directly into a LangGraph checkpointer.

## Evaluation and manifest

`data/evaluation/expected_cashflow.json` contains the deterministic forecast oracle, daily cash positions, invoice eligibility, and hypothetical collection outcomes. `cases.jsonl` contains one JSON object per case. `rubric.json` describes deterministic release gates and dimensions for human quality review. See the evaluation guide before using these files.

`data/dataset_config.json` defines the fixed date, seed, currency conventions, tenant IDs, period, and schema version. `manifest.json` records table counts, document/case/scenario counts, and the size and SHA-256 hash of every generated file except the manifest itself.

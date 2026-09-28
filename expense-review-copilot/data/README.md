# Data

Nothing here is generated at initialization. Contents of `raw/` and `processed/` are gitignored; only this file and the `.gitkeep` files are versioned.

## raw/

Inputs exactly as received from card and reimbursement exports (CSV), receipts (PDF or images), and the expense policy (Markdown or PDF).
- Never edited in place. A correction is a new file, and the original stays.
- One subdirectory per source: `raw/<source>/<YYYY-MM-DD>/`.
- Record where each file came from and when, in `raw/<source>/SOURCE.md`.
- No credentials, and no real personal data without an approved basis. Receipts often show card digits, names, and addresses; use synthetic or redacted files until a basis is approved.

The two importers read these layouts today:
- `raw/expenses/<YYYY-MM-DD>/expenses.csv`, with a header of exactly the `ExpenseRecord` fields in any order (`tenant_id`, `expense_id`, `submitted_by`, `merchant`, `expense_date`, `posted_date`, `amount_cents`, `currency`, `category`, `receipt_id`, `updated_at`). A blank `receipt_id` means the receipt is missing. An optional `preferences.json` beside it holds approved reviewer preferences. Load with `uv run expense data-import --directory ../data/raw/expenses/<date>`.
- `raw/documents/<YYYY-MM-DD>/index.json` plus one subdirectory per tenant (`tenant_alpha/…`). Each index entry records the file's path, type (`policy`, `receipt`, or `correspondence`), version, effective date, and SHA-256. Index with `uv run expense index-documents --directory ../data/raw/documents/<date>`.

## processed/

Derived only by versioned code from `raw/`.
- Reproducible: deleting `processed/` and rerunning the pipeline must give the same result.
- Each output records the inputs and code version that produced it.
- Application code reads `processed/` or the database, never `raw/`. The importer and document indexer are the only code that read `raw/`, and they write to the ignored `backend/data/app.db` database.

## Planned

Normalizing real card and bank exports into `expenses.csv`, extracting text from receipt PDFs and images, and the duplicate and missing-receipt candidate tables arrive with the planning phases. None of them exist yet.

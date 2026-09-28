# Data

Nothing here is generated at initialization. Contents of `raw/` and `processed/` are gitignored; only this file and the `.gitkeep` files are versioned.

## raw/

Inputs exactly as received, for example exports (CSV), documents (PDF or Markdown), and API dumps.
- Never edited in place. A correction is a new file, and the original stays.
- One subdirectory per source: `raw/<source>/<YYYY-MM-DD>/`.
- Record where each file came from and when, in `raw/<source>/SOURCE.md`.
- No credentials, and no real personal data without an approved basis.

The two importers read these layouts today:
- **Records:** `raw/<source>/<YYYY-MM-DD>/example_records.csv`, with a header of exactly the `ExampleRecord` fields in any order (`tenant_id`, `record_id`, `owner_id`, `name`, `category`, `amount_cents`, `currency`, `opened_on`, `closed_on`, `updated_at`). Blank cells become empty values. An optional `preferences.json` beside it holds approved preferences. Load with `uv run template-cli data-import --directory ../data/raw/<source>/<date>`.
- **Documents:** `raw/documents/<YYYY-MM-DD>/index.json` plus one subdirectory per tenant (`tenant_alpha/…`). Each index entry records the file's path, type, version, effective date, and SHA-256. Index with `uv run template-cli index-documents --directory ../data/raw/documents/<date>`.

Rename `example_records.csv` and its fields when the example record is replaced; see "Adapting the examples" in the project README.

## processed/

Derived only by versioned code from `raw/`.
- Reproducible: deleting `processed/` and rerunning the pipeline must give the same result.
- Each output records the inputs and code version that produced it.
- Application code reads `processed/` or the database, never `raw/`. The importer and document indexer are the only code that read `raw/`, and they write to the ignored `backend/data/app.db` database.

## Planned

Which raw inputs are expected, and which phase introduces their pipeline, comes from the project plan.

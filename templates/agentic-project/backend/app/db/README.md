# `db/` — relational storage

Tenant-owned records, from the contract that validates a row, to the table that stores it, to the repository that reads it back and the importer that loads it from CSV. The default database is a local SQLite file (`backend/data/app.db`). The code uses SQLAlchemy Core with async drivers, so a PostgreSQL URL (`postgresql+asyncpg://…`) switches the dialect without changing repositories.

Three invariants hold everywhere in this package:

1. **Every tenant-owned row is keyed by `(tenant_id, <key>)`**, and every read takes a `TenantScope`. Another tenant's row with the same key is invisible; it looks exactly like a missing one.
2. **Money is integer cents** (`amount_cents: int`), never floats.
3. **No free-form SQL** is accepted from callers, and no tenant chosen by a model.

## Files

### `records.py` — row contracts

- **`TenantRecord`**: the base of every tenant-owned row. It has `tenant_id` (validated against `TENANT_ID_PATTERN`), a class-level `key_field` naming the field that is unique within a tenant, and the `record_key` property returning that field's value. Repositories use `key_field` so one generic implementation serves every record type.
- **`ExampleRecord`**: the example to replace with your first real record type. It demonstrates every pattern a record needs: a tenant-scoped key (`record_id`), integer cents (`amount_cents`), an optional field (`closed_on`), an aware timestamp (`updated_at: AwareDatetime`), and a cross-field rule (`validate_dates`: `closed_on` cannot precede `opened_on`).
- **`RECORD_KEY_PATTERN`** (`^[A-Za-z0-9][A-Za-z0-9_.-]*$`): keys appear in paths, logs, and tool arguments, so they are restricted to a safe alphabet.

### `tables.py` — SQLAlchemy Core tables

| Table | Key | Holds |
|---|---|---|
| `example_records` | `(tenant_id, record_id)` | `ExampleRecord` rows; columns match the contract's fields |
| `memory_preferences` | `(tenant_id, preference_id)` | Preferences; a composite foreign key `(tenant_id, record_id)` → `example_records` |
| `conversation_threads` | `thread_id` | Which tenant owns each thread |
| `conversation_messages` | `(thread_id, sequence)` | One JSON message per row |
| `document_chunks` | `(tenant_id, index_version, chunk_id)` | Chunk text and its vector as a JSON array, indexed by `(tenant_id, index_version, document_id)` |

Why composite foreign keys: a preference in `tenant_alpha` can only reference a record in `tenant_alpha`, and the database enforces it, not just the code.

**`UtcDateTime`** is a column type that stores aware datetimes as UTC ISO-8601 text and refuses naive ones. SQLite has no timezone-aware type; fixed-format UTC text keeps ordering correct and round-trips on every dialect.

The schema is created with `metadata.create_all` (see `engine.py`) until migrations are introduced. That call creates missing tables but **does not alter existing ones**: after changing a column, delete `backend/data/app.db` locally, or add a migration tool before production data exists.

### `engine.py` — the engine's lifetime

- `build_database_url(state_dir, configured_url)` returns `TEMPLATE_DATABASE_URL` if set, else `sqlite+aiosqlite:///<backend/data>/app.db`.
- `open_database(url)` is an async context manager: it creates the engine, runs `ensure_database_schema`, yields the engine, and always disposes of it.
- For SQLite, `_create_engine` creates the file's directory and registers `_enable_sqlite_foreign_keys`, because SQLite ignores foreign keys unless `PRAGMA foreign_keys=ON` is set on every connection.
- A malformed URL raises `ConfigurationError("invalid_database_url: check TEMPLATE_DATABASE_URL")`, which names the variable and never the URL (it may contain a password).

### `repository.py` — tenant-scoped storage

`RecordRepository[RecordT]` is the ABC with three methods:

| Method | Behavior |
|---|---|
| `save_records(records)` | Insert new rows and replace existing ones with the same tenant and key; atomic, and idempotent (saving the same rows again changes nothing) |
| `get_record(scope, key)` | The tenant's row, or `RecordNotFoundError` |
| `list_records(scope, *, limit)` | Up to `limit` rows (1 to `MAX_LIST_LIMIT` = 500) ordered by key; out-of-range limits raise `InvalidQueryError` |

Two implementations honor it:

- **`SqlRecordRepository(engine, table, record_type)`**: one generic implementation for any table whose columns match the record's fields. Writes use update-then-insert inside one transaction, which is portable across SQLite and PostgreSQL, unlike each dialect's own upsert syntax. Every row read back is validated against the record contract.
- **`InMemoryRecordRepository`**: a dictionary-backed fake for tests. One parametrized test suite runs against both implementations, so the fake cannot drift from the real one.

### `csv_import.py` — loading CSV exports

- `load_csv_records(path, record_type)` reads a CSV whose header names **exactly** the contract's fields (in any order), turns empty cells into `None`, and validates every row. It collects all problems before failing, and the message names lines, fields, and error types, never cell values: `invalid_csv_rows: example_records.csv: 2 invalid rows: line 3: amount_cents (int_parsing); …`.
- `import_structured_data(directory, engine)` validates **every** file in `STRUCTURED_SOURCES` before writing any of them, then writes them in order. A bad file therefore writes nothing.
- `STRUCTURED_SOURCES` binds each file name to its contract and table. Order matters: parents come before children, so composite foreign keys resolve.
- `ImportReport` is the per-file result (`table`, `source`, `rows_read`, `rows_written`).

Rows are validated with `strict=False` here only: CSV cells are always text, so `"4250"` must become `4250`. Everywhere else contracts are strict.

## How it connects

- `foundation.py` opens the engine and builds `SqlRecordRepository` instances for `example_records` and `memory_preferences`; `import_seed_data` calls `import_structured_data`.
- `memory/`, `rag/`, and `tools/` receive repositories or the engine; none of them builds its own.
- `mcp/examples_server.py` opens its own engine in the server process.

## How to use

```bash
cd backend
.venv/bin/template-cli data-import --directory ../data/raw/<source>/<YYYY-MM-DD>
```

The directory holds `example_records.csv` and, optionally, `preferences.json`; see [`data/README.md`](../../../data/README.md). From code:

```python
from app.core.context import TenantScope
from app.foundation import Foundation


async def list_open_records(foundation: Foundation) -> list[str]:
    scope = TenantScope(tenant_id="tenant_alpha")
    records = await foundation.example_records.list_records(scope, limit=100)
    return [record.record_id for record in records if record.closed_on is None]
```

## How to replace `ExampleRecord` with a real record type

Rename in one change and keep `./scripts/check.sh` green:

1. `records.py`: define the new `TenantRecord` subclass, with `key_field`, a `Field(description=...)` on every field, integer cents for money, and a `model_validator` for cross-field rules.
2. `tables.py`: a table keyed by `_build_key_column("tenant_id")` plus the key column, with columns matching the fields exactly. Update `memory_preferences`' foreign key if preferences refer to it.
3. `csv_import.py`: replace the entry in `STRUCTURED_SOURCES`, keeping parent tables first.
4. `foundation.py`: the `Foundation` attribute and its `SqlRecordRepository`.
5. `tools/examples.py`, `mcp/examples_server.py`, and `tests/synthetic.py`, which follow the record's fields.

The project README's "Adapting the examples" table lists every file involved.

## Tests

`tests/test_db.py`: the contracts, the CSV header and row validation, atomic and idempotent saves, tenant isolation, and the parametrized repository contract suite over both implementations.

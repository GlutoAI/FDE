# Expense Review Copilot — Backend

FastAPI backend with a SQLite database, the model layer (one `BaseAgent`, a provider per vendor), and the startup foundations: CSV import, embeddings and retrieval, memory, and one expense tool served over MCP. See the [project README](../README.md) for what is implemented and what is planned.

## Prerequisites

- Python 3.12

## Setup

From the `backend/` directory, either with uv (the lock file is the source of truth):

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install uv
.venv/bin/uv sync --locked
```

or with pip, using `requirements.txt` exported from the same lock:

```bash
python3.12 -m venv .venv
source .venv/bin/activate  # macOS/Linux
python -m pip install -r requirements.txt
```

The pip route installs runtime dependencies only: no tests, lint, or the `expense` command (use `python -m app.cli` instead). After changing dependencies in `pyproject.toml`, run `uv lock`, then `uv export --frozen --no-dev --no-hashes --no-emit-project -o requirements.txt`.

## Run the server

From the `backend/` directory:

```bash
.venv/bin/uvicorn app.main:app --reload
```

The server is available at **http://localhost:8000**. Startup loads settings from `../.env` and `config/`, and opens the database; it makes no model call.

## Endpoints

### GET /health

Returns the application and database status.

```bash
curl http://localhost:8000/health
```

```json
{"status": "ok", "db": "connected"}
```

On a database failure it returns 503 with `{"status": "error", "db": "disconnected", "detail": "database_unavailable"}`.

### POST /diagnostics/connection

Runs the connection agent through the fixture model, even when the settings select live mode, and returns the validated output with its provenance. No HTTP route makes a paid request.

## CLI

```bash
.venv/bin/expense config-check
.venv/bin/expense smoke                     # add --live --provider openai|anthropic for one hosted request
.venv/bin/expense data-import --directory ../data/raw/expenses/<date>
.venv/bin/expense index-documents --directory ../data/raw/documents/<date>   # add --live for OpenAI embeddings
.venv/bin/expense search --tenant tenant_alpha --query "are receipts required for meals"
.venv/bin/expense mcp-check --tenant tenant_alpha
```

`data/` is empty at initialization, so `data-import` and `index-documents` need an import directory in the layouts described in [data/README.md](../data/README.md).

## Checks

```bash
.venv/bin/pytest
.venv/bin/ruff check app tests
.venv/bin/mypy
```

Tests write synthetic data into temporary directories (`tests/synthetic.py`); they never read `data/`.

## Database

The SQLite database is stored at `data/app.db`, i.e. `backend/data/app.db`, and is created on first start. `backend/data/` is gitignored; it also holds the MCP server logs (`mcp-<server>.log`). Set `EXPENSE_DATABASE_URL` in `../.env` to use another database.

## Layout

```text
backend/
  app/
    main.py          # FastAPI app and lifespan
    database.py      # Engine dependency and SELECT 1 check for routes
    routers/         # health, diagnostics
    core/            # settings, errors, tenant scope, clock
    llm/             # contracts, provider ABC, providers/ (fixture, openai, anthropic), prompt loader, runtime
    agents/          # BaseAgent, connection/ (agent and its contracts)
    prompts/         # versioned YAML prompts
    db/              # records, tables, engine, repositories, CSV import
    rag/             # embedders, vector store, ingestion, retriever
    memory/          # preferences, conversation history
    tools/           # BaseTool, expense tools
    mcp/             # MCP server builder, expenses server, role-filtered client
    bootstrap.py     # model provider and embedder factories
    foundation.py    # open_foundation(): database, RAG, memory, MCP catalog
    cli.py
  config/            # default, local, test, models, mcp TOML
  tests/
  data/              # ignored: app.db, MCP logs
```

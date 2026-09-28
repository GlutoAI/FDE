# Cashflow Copilot — Backend

FastAPI backend with a SQLite database, the model layer (one `BaseAgent`, a provider per vendor), and the startup foundations: CSV import, embeddings and retrieval, memory, and tools served over MCP. See the [project README](../README.md) for what is implemented and what is planned.

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

The pip route installs runtime dependencies only: no tests, lint, or the `cashflow` command (use `python -m app.cli` instead). After changing dependencies in `pyproject.toml`, run `uv lock`, then `uv export --frozen --no-dev --no-hashes --no-emit-project -o requirements.txt`.

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
.venv/bin/cashflow config-check
.venv/bin/cashflow smoke                     # add --live --provider openai|anthropic for one hosted request
.venv/bin/cashflow data-import
.venv/bin/cashflow index-documents           # add --live for OpenAI embeddings
.venv/bin/cashflow search --tenant tenant_aurora --query "disputed invoice reminder"
.venv/bin/cashflow mcp-check --tenant tenant_aurora
```

## Checks

```bash
.venv/bin/pytest
.venv/bin/ruff check app tests
.venv/bin/mypy
```

## Database

The SQLite database is stored at `data/app.db`, i.e. `backend/data/app.db`, and is created on first start. `backend/data/` is gitignored; it also holds the MCP server logs (`mcp-<server>.log`). Set `CASHFLOW_DATABASE_URL` in `../.env` to use another database.

## Layout

```text
backend/
  app/
    main.py          # FastAPI app and lifespan
    database.py      # Engine dependency and SELECT 1 check for routes
    routers/         # health, diagnostics
    core/            # settings, errors, tenant scope, clock
    llm/             # contracts, provider ABC, providers, prompt loader, runtime
    agents/          # BaseAgent, connection agent
    prompts/         # versioned YAML prompts
    db/              # records, tables, engine, repositories, CSV import
    rag/             # embedders, vector store, ingestion, retriever
    memory/          # preferences, conversation history
    tools/           # BaseTool, finance tools
    mcp/             # MCP server builder, finance server, role-filtered client
    bootstrap.py     # model provider and embedder factories
    foundation.py    # open_foundation(): database, RAG, memory, MCP catalog
    cli.py
  config/            # default, local, test, models, mcp TOML
  tests/
  data/              # ignored: app.db, MCP logs
```

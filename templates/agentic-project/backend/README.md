# Agentic Project Template — Backend

FastAPI backend with a SQLite database, the model layer (one `BaseAgent`, a provider per vendor), and the startup foundations: CSV import, embeddings and retrieval, memory, and one example tool served over MCP. See the [project README](../README.md) for what is implemented and what is planned.

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

The pip route installs runtime dependencies only: no tests, lint, or the `template-cli` command (use `python -m app.cli` instead). After changing dependencies in `pyproject.toml`, run `uv lock`, then `uv export --frozen --no-dev --no-hashes --no-emit-project -o requirements.txt`.

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
.venv/bin/template-cli config-check
.venv/bin/template-cli smoke                     # add --live --provider openai|anthropic for one hosted request
.venv/bin/template-cli data-import --directory ../data/raw/<source>/<date>
.venv/bin/template-cli index-documents --directory ../data/raw/documents/<date>   # add --live for OpenAI embeddings
.venv/bin/template-cli search --tenant tenant_alpha --query "what needs a supporting document"
.venv/bin/template-cli mcp-check --tenant tenant_alpha
```

`data/` is empty at initialization, so `data-import` and `index-documents` need an import directory in the layouts described in [data/README.md](../data/README.md).

## Checks

`../scripts/check.sh` runs everything below plus the frontend build. Individually:

```bash
.venv/bin/pytest
.venv/bin/ruff check app tests
.venv/bin/ruff format --check app tests
.venv/bin/mypy
```

Tests write synthetic data into temporary directories (`tests/synthetic.py`); they never read `data/`. `tests/conftest.py` removes `TEMPLATE_*` and vendor variables from the environment and makes any socket connection fail the test. Tests use a temporary project root, so the real `.env` is never read and the suite cannot reach a hosted API.

## How it fits together

Three composition roots build everything; every other module receives its collaborators through `__init__` and depends only on the abstract base classes:

- `main.py` builds the HTTP app. Its lifespan loads settings and opens one database engine.
- `bootstrap.py` builds model-side objects: it resolves a model profile from `config/models.toml`, opens that vendor's SDK client, and wraps it in a `ModelProvider`.
- `foundation.py` builds the startup bases (repositories, memory, embedder, vector store, retriever, MCP catalog) over one engine, for the CLI.

An agent call runs as follows (`BaseAgent.run_agent`):

1. Deterministic: the request is revalidated against the agent's Pydantic input model.
2. **Model judgement:** Pydantic AI sends one request (no retries, no tool calls, bounded by the profile's timeout and token cap), and the model writes the structured output.
3. Deterministic: Pydantic validates the output against its schema, and the agent's `_validate_output` checks rules that relate output to input.
4. Deterministic: the application attaches provenance (provider, model, prompt version and SHA-256, token usage). The model cannot set any of it.

Everything else is deterministic code: CSV import, chunking, embedding-based ranking (vector similarity, not an LLM), preference expiry, tenant filtering, and tool execution. In a tool call, the model chooses the tool and its arguments; `BaseTool.call_tool` validates them and enforces the deadline, and the tenant always comes from the server-side `ToolContext`.

Errors are subclasses of `AppError` whose messages are fixed codes (`storage_failed: ...`). Only the boundaries catch them (the CLI, the HTTP routes, and the MCP server), and they pass on only `str(error)`; provider response bodies, keys, and row values never appear in a message.

## Database

The SQLite database is stored at `data/app.db`, i.e. `backend/data/app.db`, and is created on first start. `backend/data/` is gitignored; it also holds the MCP server logs (`mcp-<server>.log`). Set `TEMPLATE_DATABASE_URL` in `../.env` to use another database.

## Layout

```text
backend/
  app/
    main.py          # FastAPI app and lifespan
    database.py      # Engine dependency and the SELECT 1 reachability check for routes
    routers/         # health, diagnostics
    core/            # settings, errors, tenant scope, clock
    llm/             # contracts, provider ABC, providers/ (fixture, openai, anthropic), prompt loader, runtime
    agents/          # BaseAgent, connection/ (agent and its contracts)
    prompts/         # versioned YAML prompts
    db/              # records, tables, engine, repositories, CSV import
    rag/             # embedders, vector store, ingestion, retriever
    memory/          # preferences, conversation history
    tools/           # BaseTool, the example tool
    mcp/             # MCP server builder, example server, role-filtered client
    bootstrap.py     # model provider and embedder factories
    foundation.py    # open_foundation(): database, RAG, memory, MCP catalog
    cli.py
  config/            # default, local, test, models, mcp TOML
  tests/
  data/              # ignored: app.db, MCP logs
```

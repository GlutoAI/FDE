# Agentic Project Template

PURPOSE: one sentence saying who this helps, with what decision, and where a person stays in control.

**Status:** this is the initial skeleton. It contains:
- a FastAPI backend with validated settings, a model catalog for OpenAI and Anthropic, typed Pydantic AI contracts, one `BaseAgent`, and a connection agent that runs offline through a fixture model;
- tested startup bases: a SQLite database with CSV import (PostgreSQL by URL later), embeddings with a vector store and retriever, preference and conversation memory, and one read-only example tool served by a stdio MCP server;
- a React frontend that calls the backend, and an empty `data/` layout;
- Docker Compose for the API and the UI, with no secrets in either container.

The record, tool, and documents are neutral **examples** (`ExampleRecord`, `get_example_record`, a two-tenant policy corpus in the tests) that show each base working. No business agent, business tool, or workflow exists yet. Authentication, PostgreSQL/pgvector, and the other containers (worker, database, MCP services) are planned, not built. Default tests and startup stay offline; only commands given `--live` call hosted APIs.

## Start here

    ./scripts/check.sh            # offline gate: backend tests, lint, types, frontend build
    ./scripts/check.sh --docker   # the same, plus the Compose stack

Or step by step:

    cd backend && uv sync --locked && uv run pytest && uv run template-cli smoke
    cd frontend && npm ci && npm run build

To run both: `uv run uvicorn app.main:app --reload` in `backend/`, then `npm run dev` in `frontend/`, and open http://localhost:5173. Or, from the project root, `docker compose -f docker/compose.yaml up --build` and open http://localhost:3000; `down` stops it, and `down -v` also deletes the database volume. See [backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md).

## Local API keys and secrets

Keys live only in **`.env`** at the project root. It is created from `.env.example` if absent, set to `chmod 600`, and gitignored. The backend reads it; the frontend never does. Each vendor has its own key (`TEMPLATE_OPENAI_API_KEY`, `TEMPLATE_ANTHROPIC_API_KEY`). A live check is `uv run template-cli smoke --live --provider <openai|anthropic>`, one request, run only on purpose.

## Data

See [data/README.md](data/README.md). `raw/` holds inputs exactly as received; `processed/` holds what code derives from them. Both are empty at initialization and their contents are never committed.

## Adapting the examples

Each base ships with one example so it runs and is tested. Replace an example when its phase begins, not before:

| Base | Example now | Replace with | Files |
|---|---|---|---|
| Records and CSV import | `ExampleRecord`, table `example_records`, file `example_records.csv` | The first real CSV's record type | `app/db/records.py`, `app/db/tables.py`, `app/db/csv_import.py` (`STRUCTURED_SOURCES`), `app/foundation.py` |
| Tools and MCP | `get_example_record` on server `examples`, role `example_reader` | The first real read-only tool | `app/tools/examples.py`, `app/mcp/examples_server.py`, `config/mcp.toml` |
| Documents (RAG) | Types `policy`, `reference`, `correspondence` | The project's document types | `app/rag/contracts.py` (`DocumentEntry.document_type`) |
| Memory | Preferences keyed to a record by `record_id` | The record a preference refers to | `app/memory/preferences.py`, `memory_preferences` in `app/db/tables.py` |
| Agents | The connection agent and prompt `v1.yaml` | Keep it as the connection probe; add business agents beside it | `app/agents/`, `app/prompts/` |
| Test data | `tests/synthetic.py` | Synthetic rows for the new record type | `tests/synthetic.py`, then `test_db`, `test_mcp`, `test_memory`, `test_foundation` |

Rename a record everywhere in one change and keep `./scripts/check.sh` green. Composite `(tenant_id, key)` keys, integer cents, and application-built `TenantScope` stay as they are.

## Verification

Not yet run for this project. Run `./scripts/check.sh --docker` and record the observed results here, with live status per vendor (passed, failed with reason, or not run).

## Next steps

1. Write the plan with the `agentic-project-planning` skill: phases, how raw data arrives, and what processing produces.
2. Replace the example record with the first real one when the first CSV is described.
3. Add the first business agent beside the connection agent, with its own Pydantic input and output models and a versioned prompt.
4. Run a live probe only when a key is supplied for that purpose.

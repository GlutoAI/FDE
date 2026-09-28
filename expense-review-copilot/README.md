# Expense Review Copilot

A local-first copilot for small businesses that flags likely duplicate expenses and missing receipts, answers expense-policy questions from the company's own documents, and prepares corrections that a person approves before anything changes.

**Status:** this is the initial skeleton. It contains:
- a FastAPI backend with validated settings, a model catalog for OpenAI and Anthropic, typed Pydantic AI contracts, one `BaseAgent`, and a connection agent that runs offline through a fixture model;
- tested startup bases: a SQLite database with an `expenses` table and CSV import (PostgreSQL by URL later), embeddings with a vector store and retriever over policy documents, preference and conversation memory, and one read-only example tool (`get_expense`) served by a stdio MCP server;
- a React frontend that calls the backend, and an empty `data/` layout;
- Docker Compose for the API and the UI, with no secrets in either container.

None of the four product capabilities is built yet. The expense record carries the fields that duplicate detection and missing-receipt checks will need (merchant, dates, amount, a nullable `receipt_id`), and the retriever can already search policy text, but there is no duplicate detector, no missing-receipt report, no policy-answering agent, and no correction or approval workflow. Business agents, authentication, PostgreSQL/pgvector, and the other containers (worker, database, MCP services) are planned, not built. Default tests and startup stay offline; only commands given `--live` call hosted APIs.

## Start here

    cd expense-review-copilot/backend && uv sync --locked && uv run pytest && uv run expense smoke
    cd expense-review-copilot/frontend && npm ci && npm run build

To run both: `uv run uvicorn app.main:app --reload` in `backend/`, then `npm run dev` in `frontend/`, and open http://localhost:5173. Or, from the project root, `docker compose -f docker/compose.yaml up --build` and open http://localhost:3000; `down` stops it, and `down -v` also deletes the database volume. See [backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md), which keep the template's sections.

## Local API keys and secrets

Keys live only in **`expense-review-copilot/.env`**. It is created from `.env.example` if absent, set to `chmod 600`, and gitignored. The backend reads it; the frontend never does. Each vendor has its own key (`EXPENSE_OPENAI_API_KEY`, `EXPENSE_ANTHROPIC_API_KEY`). A live check is `uv run expense smoke --live --provider <openai|anthropic>`, one request, run only on purpose.

## Data

See [data/README.md](data/README.md). `raw/` holds inputs exactly as received; `processed/` holds what code derives from them. Both are empty at initialization and their contents are never committed.

## Verification

Observed on 2026-09-27:
- Backend: 182 tests pass; `ruff check`, `ruff format --check`, and strict `mypy` are clean. Tests write synthetic data into temporary directories and never read `data/`.
- CLI, on synthetic import directories: `data-import` read 4 expenses and 3 preferences, and a rerun gave the same result; `index-documents` indexed 2 documents; `search` returned only the asking tenant's policy; `mcp-check` started the stdio server and verified the `expense_reader` role; `smoke` returned `CONNECTION_OK` through the fixture model.
- API and UI: `/health` returned `{"status":"ok","db":"connected"}` directly and through the Vite proxy; the connection diagnostic returned `CONNECTION_OK`; the page rendered the health result. `npm ci` and `npm run build` succeeded; `npm audit` reports 2 findings (1 moderate, 1 high) in the template's frontend dependencies, not yet addressed.
- Docker: both services became healthy; the same checks passed through nginx on port 3000; processes run as `app` and `nginx`; the image holds no `.env` file; the services receive only `EXPENSE_ENV` and `EXPENSE_MODEL_MODE`; `smoke` and `mcp-check` passed inside the API container; the database survived a restart.
- Live model calls: not run for OpenAI or Anthropic. `.env` has no keys yet.

## Roadmap

No planning documents yet. Run the `agentic-project-planning` skill to produce `docs/`; its phases describe proposed work, not built work.

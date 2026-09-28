# Cash-Flow and Collections Copilot

A learning project for a production-oriented, multi-agent assistant that helps a small business understand cash shortages, investigate overdue invoices, and prepare reminders for human approval.

This milestone contains **synthetic data, a reproducible generator, a validator, evaluation fixtures, a working LLM initialization foundation** (typed contracts, a provider ABC, a shared agent base, model configuration, YAML prompts, and a connection agent), and **tested bases for a database, RAG, memory, and MCP tools** (see [Foundations](#foundations-database-rag-memory-and-mcp-tools)), served by a **FastAPI backend and a React frontend** in the workspace's standard `backend/` + `frontend/` layout, and runnable locally or with **Docker Compose** (API and UI). Business agents, authentication, PostgreSQL/pgvector, and the remaining Compose services (worker, database, MCP, identity, telemetry) remain planned. **We build and demonstrate everything locally first; AWS deployment is an optional future track.** Data scripts and default tests stay offline; only commands given `--live` call hosted APIs.

## Implementation roadmap

The detailed plan starts with the proposed directory structure and architecture, then gives ordered tasks and acceptance gates. The required local path is phases 00–17 plus MCP milestone 06A, followed by local handoff in 19. AWS phase 18 is optional and deferred; A2A milestone 10A is conditional and can run locally:

- [Step-by-step implementation plan](docs/implementation_plan.md): configuration, domain models, database, auth, shared model foundation, tools, RAG, agents, memory, approvals, API, UI, integrations, and rollout.
- [Model and agent runtime plan](docs/agent_runtime_plan.md): model profiles, the shared execution harness, typed agent contracts, tool permissions, bounded loops, budgets, retries, and recovery.
- [MCP servers and A2A decision plan](docs/mcp_a2a_plan.md): finance, evidence, and collections tool servers; database access through authorized MCP tools; client integration, protocol/auth testing, and optional independent-agent delegation.
- [Golden datasets and evaluation harness plan](docs/evaluation_harness_plan.md): test isolation, scenario adapters, deterministic/semantic graders, holdouts, reports, release gates, and the improvement loop.
- [Local Docker and optional AWS plan](docs/deployment_plan.md): local services, authentication, queues, monitoring, backups, rollback, and runbooks, followed by a separate optional cloud design.

These documents describe the remaining roadmap and identify the small foundation already implemented. The connection probe is not a business agent or a production quality evaluation.

Agents will use MCP clients to call finance, evidence, and draft tools. MCP servers enforce permissions and call the underlying PostgreSQL/pgvector services. LangGraph coordinates the internal specialists; A2A is optional for a separately deployed receivables reviewer. Approval and sending remain controlled by the application.

Local completion requires no AWS account, Cognito, SQS, S3, or CloudWatch. Use local identity, PostgreSQL/pgvector, a durable local job queue, document volumes, and local telemetry. Model inference is separately configurable: fake models support offline contract tests; real local models or selected hosted APIs support actual quality evaluation without cloud deployment. Real QuickBooks/messaging connections are optional integration exercises.

## Local API keys and secrets

Keep actual developer API keys and application secrets in **`cashflow-copilot/.env`**, at this project's root, alongside this README. The local file has owner-only permissions. Put the OpenAI key in `CASHFLOW_LLM_API_KEY`; this project explicitly passes it to the provider and does not read an `OPENAI_API_KEY` alias. The existing data scripts need no keys.

- [`.env.example`](.env.example) contains the versionable template with empty secret values and fixture defaults.
- `.env` and `.env.*` are ignored by Git, except the approved `.env.example` template.
- [`.dockerignore`](.dockerignore) excludes environment files from Docker build contexts.
- The Pydantic Settings loader reads the project's `.env` explicitly; existing process environment variables take precedence. Missing secrets are errors only for enabled components.
- Secrets stay out of prompts, logs, traces, reports, and committed TOML files. The configuration-check command reports key presence only.

On a fresh checkout, create `.env` from `.env.example` only if it does not already exist, and restrict its permissions to the file owner (`chmod 600 .env` on macOS/Linux). Do not overwrite an existing developer file. The initial settings loader handles local/test environments and the LLM probe; infrastructure fields in the template are reserved for later phases. TOML settings reject unknown fields; unused environment fields are ignored during this foundation stage.

## Run it locally

The project follows the workspace's standard layout: `backend/` (FastAPI, package `app`) and `frontend/` (Vite React TypeScript), with `.env`, `data/`, `docs/`, and `scripts/` at the project root. The backend requires Python 3.12; see [backend/README.md](backend/README.md) for the pip alternative and the full CLI.

```bash
cd backend
python3.12 -m venv .venv
.venv/bin/python -m pip install uv
.venv/bin/uv sync --locked
.venv/bin/pytest && .venv/bin/ruff check app tests && .venv/bin/mypy
.venv/bin/cashflow config-check
.venv/bin/cashflow smoke
.venv/bin/uvicorn app.main:app --reload     # http://localhost:8000/health
```

```bash
cd frontend
npm ci
npm run dev                                 # http://localhost:5173; /api is proxied to :8000
```

The page shows `/health` (application and database status) and runs the fixture connection agent through `POST /diagnostics/connection`. No HTTP route makes a paid model request.

### Or run it with Docker

From the project root; Docker installs the backend from `backend/requirements.txt` and the frontend from `frontend/package-lock.json`:

```bash
docker compose -f docker/compose.yaml up --build      # UI http://localhost:3000, API http://localhost:8000/health
docker compose -f docker/compose.yaml exec api python -m app.cli smoke
docker compose -f docker/compose.yaml down            # add -v to also delete the database volume
```

- **`api`** ([`docker/Dockerfile.api`](docker/Dockerfile.api)): Python 3.12, `pip install -r requirements.txt`, uvicorn as a non-root user. SQLite and MCP logs live in the `api-data` volume, separate from the host's `backend/data/`.
- **`ui`** ([`docker/Dockerfile.ui`](docker/Dockerfile.ui)): `npm ci` and `npm run build`, then unprivileged nginx serving the build and forwarding `/api/` to the API ([`docker/nginx.conf`](docker/nginx.conf)), the same routing as the Vite proxy.
- Ports bind to `127.0.0.1` only. Stop a local uvicorn first; both use port 8000.
- No container receives `.env` or any API key; the image contains only `app/`, `config/`, and `requirements.txt`. Live commands (`--live`) run on the host until a service is given an explicit key mapping.
- The API image sets `OPENSSL_armcap=0`: on Apple M4 hosts, the OpenSSL bundled with `cryptography` otherwise crashes (SIGILL) at import inside Docker's Linux VM.

## LLM foundation

Two vendors are supported through one `BaseAgent` and a `ModelProvider` implementation per vendor: **OpenAI GPT-5.4 mini** (`gpt-5.4-mini-2026-03-17`, the default for the `connection` role) and **Anthropic Claude Opus 5.5** (`claude-opus-5-5`). Both are configured in [`backend/config/models.toml`](backend/config/models.toml).

Model selection, from lowest to highest priority:
1. `default_profile`.
2. `roles`.
3. The prompt YAML's `model_profile`, then its `model`.
4. `CASHFLOW_LLM_MODEL`.

`CASHFLOW_LLM_PROVIDER` or `--provider` switches to that vendor's entry in `[vendor_profiles]` and drops the YAML model. `--provider` also ignores `CASHFLOW_LLM_MODEL`. Prompts live in [`backend/app/prompts/`](backend/app/prompts/); the current one is `connection/v2.yaml`.

Each vendor has its own key in the ignored `.env`: `CASHFLOW_LLM_API_KEY` (OpenAI) and `CASHFLOW_ANTHROPIC_API_KEY`. `cashflow config-check` reports only whether each key is present. After setting a key, explicitly run one hosted request to that vendor:

```bash
cd backend
.venv/bin/cashflow smoke --live --provider openai
.venv/bin/cashflow smoke --live --provider anthropic
```

The Anthropic SDK is pinned to `anthropic>=0.108,<1`: anthropic 1.8.0 rejects an argument Pydantic AI 2.31.1 sends, before any request is made.

`smoke` always selects a fixture provider; `--live` is required for hosted inference even if the environment specifies live mode. The live command has no tools, retries, conversation memory, or business data. It validates a fixed response marker and reports safe metadata. Missing credentials, authentication/permission, quota/rate limits, network/timeouts, or invalid output produce a nonzero exit; no failure falls back to fixtures. Model response storage is disabled in this request.

**Current live results, 2026-09-27, prompt version 2, via `smoke --live --provider`:**
- **Anthropic:** passed with `claude-opus-5-5` (380 input and 25 output tokens) using native structured output.
- **OpenAI:** passed with `gpt-5.4-mini-2026-03-17` (135 input and 19 output tokens).

At the time of these live results, all 89 offline tests passed and Ruff and strict mypy were clean. The OpenAI snapshot is documented in the [official GPT-5.4 mini documentation](https://developers.openai.com/api/docs/models/gpt-5.4-mini). For Claude models, see the [Anthropic models overview](https://docs.claude.com/en/docs/about-claude/models/overview).

**Earlier result, 2026-09-27:** the connection agent passed with `gpt-5.4-mini-2026-03-17` on prompt version 1, 37 input tokens and 7 output tokens.

**Previous live result, 2026-09-27:** the connection agent passed with `gpt-4.1-mini-2025-04-14`, prompt version 1, 38 input tokens and 4 output tokens. This verifies access to that configured model at that time; business-agent quality remains unevaluated. The model is a diagnostic choice, not the selected business-agent model. See the [OpenAI Responses quickstart](https://developers.openai.com/api/docs/quickstart).

Initialization order: validated settings and contracts → provider ABC and fixture/live implementations → YAML loader → injected `BaseAgent` → `ConnectionAgent` → offline tests → explicitly requested live check. Constructors make no requests. Phase 05 will extend this foundation with authorized execution context, tool loops, budgets, and telemetry, using the planned Pydantic AI runtime.

## Foundations: database, RAG, memory, and MCP tools

`open_foundation()` in [`foundation.py`](backend/app/foundation.py) is the one place that composes every base at startup. It opens the database and creates its tables, then opens the embedder and builds the repositories, vector store, retriever, memory stores, and MCP catalog. Every base is an ABC with an in-memory fake and a real implementation, and one parametrized contract test runs against both. Every read and write takes a `TenantScope` supplied by application code, never by a model.

| Base | Real implementation now | Planned replacement |
| --- | --- | --- |
| Database (`db/`) | SQLAlchemy async Core on SQLite, `backend/data/app.db`; composite `(tenant_id, key)` primary and foreign keys | PostgreSQL via `CASHFLOW_DATABASE_URL`, Alembic migrations |
| CSV import (`db/csv_import.py`) | Customers and invoices validated through Pydantic records; all files are checked before any row is written | More tables as agents need them |
| Embeddings (`rag/embedder.py`) | Offline `HashingEmbedder`; OpenAI `text-embedding-3-small` at 512 dimensions through Pydantic AI | Any profile in `[embedding_profiles]` |
| Vectors (`rag/vector_store.py`) | JSON vectors in SQLite, filtered by tenant and index version, then exact cosine ranking | pgvector |
| Memory (`memory/`) | Approved preferences with validity windows; conversation history as Pydantic AI messages per tenant-owned thread | Summarization, retention policy |
| Tools and MCP (`tools/`, `mcp/`) | `BaseTool` with argument validation and a deadline; a stdio finance server; per-role allowlists in [`backend/config/mcp.toml`](backend/config/mcp.toml) | Authenticated HTTP transport, evidence and collections servers |

Run the offline pipeline from `backend/`:

```bash
.venv/bin/cashflow data-import                  # idempotent upsert of customers, invoices, preferences
.venv/bin/cashflow index-documents              # 27 documents -> 33 chunks, fixture embeddings
.venv/bin/cashflow search --tenant tenant_aurora --query "disputed invoice reminder"
.venv/bin/cashflow mcp-check --tenant tenant_aurora   # launches the server per role, checks its tool list
```

`index-documents --live` and `search --live` use OpenAI embeddings and `CASHFLOW_LLM_API_KEY`; Anthropic has no embeddings API. Each embedding profile gets its own index version (`provider:model:dimensions`), so fixture and live vectors never mix. The MCP server runs as a child process with only `PATH`, the database URL, and fixture mode in its environment. It receives no API keys and writes its logs to `backend/data/mcp-<server>.log`.

**Live embedding result, 2026-09-27:** indexing sent 33 chunks in one request (3,699 input tokens). The query "Can we send a reminder while a customer disputes an invoice?" for `tenant_aurora` ranked Aurora's collections-policy dispute rule first (0.65), then the Willow dispute email; all five results were Aurora documents. This verifies the connection and tenant filtering, not retrieval quality.

Deliberate shortcuts:
- Tables are created with `create_all`; there are no migrations yet.
- Vector search loads a tenant's chunks and ranks them in Python. That is fine for 33 chunks but not for a real corpus.
- An MCP server's tenant is fixed at launch rather than authenticated per request.
- `list_customer_invoices` filters in Python.
- Preference reads cap at 500 rows.
- A truncated conversation window can begin with an orphaned tool result.
- The offline hashing embedder matches words, not meaning, and with 256 buckets unrelated words can cancel each other out.

With these foundations and the API, 176 offline tests pass; Ruff and strict mypy are clean, the frontend builds, and the Docker Compose API and UI start healthy.

## Docker scope

**Docker is included in the required local plan.** The first slice exists: [`docker/compose.yaml`](docker/compose.yaml) runs the API and the React UI (see [Or run it with Docker](#or-run-it-with-docker)). Phase 03 adds the local database container; phase 17 completes the Compose setup: worker, PostgreSQL/pgvector, MCP servers as services, local identity, and telemetry. Documents/database state use local volumes. No AWS deployment is needed.

When a service needs a secret, Compose will read the root `.env` explicitly (`--env-file .env`) and pass only that service's required variables through its `environment` mapping. Secrets are never Docker build arguments or image-layer content, and the root `.dockerignore` keeps `.env`, tests, caches, and evaluation answers out of the build context. Base images are pinned by tag, not digest, until phase 17.

## Start here

From the parent workspace:

```bash
cd cashflow-copilot
python3 scripts/validate_data.py
```

For these data scripts only, Python 3.9 or newer is sufficient; they need no third-party dependencies, credentials, or installation steps.

To reproduce the supplied snapshot:

```bash
python3 scripts/generate_data.py
python3 scripts/validate_data.py
```

Generation overwrites the generated files under `data/`. Keep experiments and hand-edited variants outside that directory. The seed, dates, record ordering, and generated bytes are fixed. The validator checks the manifest, CSV/JSON agreement, references, dates, money, bank reconciliation, and golden forecast. It does **not** run agents or prove their quality.

## The fictional business problem

**Aurora Creative Agency** has 12 customers and is reviewing its position at **2026-09-26 12:00 UTC**. Its question is:

> Will we have enough cash for payroll in two weeks? Identify overdue invoices we should follow up on and prepare reminders for my review.

The forecast runs through October 10, 2026, inclusive. Currency is USD; monetary fields are integer cents.

| Forecast component | Amount |
| --- | ---: |
| Cash at the snapshot | $42,000 |
| Customer-scheduled receipts during the horizon | +$12,000 |
| Scheduled bills | -$22,000 |
| Scheduled payroll on October 9 | -$40,000 |
| **Projected closing cash** | **-$8,000** |

The first projected negative balance is October 9. Scheduled receipts are assumptions, not guaranteed collections. The negative result is a forecast of a funding gap; the baseline bank account has not actually overdrawn.

| Invoice | Customer | Original amount | Current balance | Treatment |
| --- | --- | ---: | ---: | --- |
| INV-A-1001 | Harbor & Pine Retail | $9,000 | $9,000 | Overdue; eligible for a reminder draft |
| INV-A-1002 | Summit Trail Fitness | $10,000 | $6,000 | $4,000 already paid; tentative $2,000 promise excluded from baseline |
| INV-A-1003 | Willow Creek Cafe | $5,000 | $5,000 | $2,000 disputed; policy holds reminders for the entire invoice |
| INV-A-1004 | Northstar Design Studio | $7,000 | $7,000 | Customer schedules payment for October 5 |
| INV-A-1005 | Maple Grove Dental | $5,000 | $5,000 | Customer schedules payment for October 8 |
| INV-A-1006 | Silverline Home Goods | $4,000 | $4,000 | Signed amendment makes it due October 25, beyond the horizon |

The two eligible overdue balances total $15,000. Collecting both before payroll would change projected closing cash to $7,000. Collecting Harbor alone would change it to $1,000. These are explicitly hypothetical scenarios.

**Copper Finch Studio** is a second tenant with three customers whose names match Aurora customers. Its Harbor invoice is $99,000. This deliberately catches systems that join, retrieve, or authorize by customer name without checking tenant membership.

## Contents

```text
cashflow-copilot/
  README.md
  .env.example                # Versioned template; .env (ignored) sits beside it
  backend/                    # FastAPI backend; see backend/README.md
    pyproject.toml  uv.lock  requirements.txt
    app/                      # main.py, database.py, routers/, core, llm, agents, prompts, db, rag, memory, tools, mcp
    config/                   # Defaults, local/test settings, model and embedding profiles, MCP catalog
    tests/                    # Offline foundation, contract, API, and MCP subprocess checks
    data/                     # Ignored: app.db and MCP server logs
  frontend/                   # Vite React TypeScript; typed client for /health and the connection check
  docker/                     # Dockerfile.api, Dockerfile.ui, nginx.conf, compose.yaml (API + UI)
  docs/
    data_dictionary.md
    evaluation_guide.md
  scripts/
    generate_data.py
    validate_data.py
  data/
    dataset_config.json
    manifest.json
    identity/                 # Businesses, users, memberships, fake connections
    structured/               # Financial records, each in JSON and CSV
    documents/
      index.json              # RAG document metadata and source paths
      tenant_aurora/           # Contracts, correspondence, policies
      tenant_copper/
    memory/                   # Explicitly approved preferences
    workflow/                 # A pending draft and conceptual paused run
    evaluation/               # Cases, answers, rubric, isolated failure fixtures
```

The snapshot contains **2 businesses, 15 customers, 53 invoices, 46 payments, 24 bills, 8 payroll records, 72 bank transactions, 27 documents, 18 evaluation cases, and 8 failure scenarios**. It includes three months of settled invoice history. JSON is the canonical typed representation; CSV files contain the same financial records for inspection or import.

## How we will use it

1. Import `identity/` and `structured/` records into tenant-scoped database tables.
2. Build deterministic balance and cash-flow tools from those tables.
3. Index only documents listed in `data/documents/index.json`, preserving tenant, customer, invoice, effective-date, and source metadata. Enforce tenant authorization before retrieval.
4. Serve financial and retrieval tools through authenticated MCP servers, then connect agent workflows through approved MCP clients/toolsets.
5. Load approved communication preferences from `memory/`; refresh financial facts from their authoritative records.
6. Display evidence and drafts in the React `frontend/`; require approval before external actions.
7. Use `evaluation/` in a separate test harness to check correctness and failure handling.

Do not index this README, the data dictionary, or `evaluation/` into the agent's RAG corpus: they describe expected answers and test setup. Do not import both JSON and CSV, which would duplicate records. Documents are evidence, not executable instructions; policy enforcement belongs in application code.

## Data boundaries

Every person, company, email, balance, contract, and event was invented for this project. Names may coincidentally resemble real entities. Emails use reserved `.example` domains. The dataset contains no passwords, access tokens, bank routing/account numbers, employee-level payroll, or real customer data. It has no connection to Intuit production systems.

These are **application-normalized fixtures**, not exact QuickBooks API responses, real identity-provider sessions, native LangGraph checkpoints, or a double-entry general ledger. Future integration adapters will translate provider records into these schemas. The payroll amounts are aggregate cash obligations; invoice tax is zero and no tax rules are modeled. A small synthetic dataset is useful for repeatable engineering exercises, but production evaluation also requires representative, permissioned data and operational testing.

See [the data dictionary](docs/data_dictionary.md) for schemas and [the evaluation guide](docs/evaluation_guide.md) for scenario handling.

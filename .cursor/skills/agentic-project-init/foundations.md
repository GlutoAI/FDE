# Startup foundations: database, RAG, memory, and MCP tools

Create these during initialization, after the LLM layer in [foundation.md](foundation.md). Most agentic projects need four things: structured records (often from CSV), document retrieval, memory, and tools. Each gets a small, tested base at initialization. Business logic still waits for its phase. Follow [coding-standards](../coding-standards/SKILL.md) throughout.

## Reference status

| Part | Reference | Status |
|---|---|---|
| All four bases, `foundation.py`, CLI commands, tests | [`cashflow-copilot/backend/app/`](../../../cashflow-copilot/backend/app/) (`db/`, `rag/`, `memory/`, `tools/`, `mcp/`, `foundation.py`) and [`backend/tests/`](../../../cashflow-copilot/backend/tests/) | Tested there on 2026-09-27: 176 offline tests (including real MCP subprocesses), and the offline CLI pipeline on its data. The live OpenAI `text-embedding-3-small` index and search passed (33 chunks, 3,699 tokens). Its imports read fixed paths under `data/` and have no `--directory` |
| Generic record, document index, example tool, `--directory` imports, and synthetic tests described below, as copied into every project | [`templates/agentic-project/backend/`](../../../templates/agentic-project/backend/): `ExampleRecord`, `get_example_record` on server `examples`, role `example_reader` | Built and tested on 2026-09-27: 182 offline tests in the template and in a generated project |
| The same bases on a real domain | [`expense-review-copilot/backend/`](../../../expense-review-copilot/backend/) | Built there on 2026-09-27: one `ExpenseRecord`, a 9-field `DocumentEntry`, `get_expense` on the `expenses` server with role `expense_reader`, and 182 offline tests. The CLI pipeline passed on synthetic import directories. Live embeddings not run |
| PostgreSQL, pgvector, migrations, authenticated MCP over HTTP | Planned phases | Not built anywhere |

Cashflow's records (customers, invoices), 15-field document index, and finance tools are its domain. A new project starts with the template's `ExampleRecord` and its read-only `get_example_record` tool. Replace them with the first real record type once its CSV is described; the project README's "Adapting the examples" table lists the files involved.

## Rules every base follows

- **ABC, fake, and real implementation.** Each owned abstraction is an ABC with an in-memory fake and a real implementation. One contract test, parametrized over both, proves they behave the same way.
- **The tenant comes from the application.** Every read and write takes `TenantScope(tenant_id)` (pattern `^tenant_[a-z0-9_]+$`), which is built by application code and never parsed from model output. Keys are composite, `(tenant_id, record_key)`; a foreign key includes `tenant_id`; the vector store filters by tenant before it ranks; a conversation thread belongs to one tenant; an MCP server's tenant is fixed when it launches.
- **No I/O in constructors.** `open_*` async context managers own engines and SDK clients and dispose of them on exit.
- **Safe errors.** Errors carry a code, and a location such as file, line, and field, but never values. Examples: `DataImportError("invalid_csv_rows: customers.csv: 1 invalid rows: line 3: payment_terms_days (int_parsing)")`, `AccessDeniedError`, and `ToolAccessError("mcp_unavailable: <server> did not start")`.
- **Nothing live by default.** Offline mode uses the fixture embedder. Hosted embeddings run only for commands given `--live`.

## Tree additions

```text
backend/
  config/
    models.toml                  # + default_embedding_profile and [embedding_profiles.*]
    mcp.toml                     # Approved servers and per-role tool allowlists
  app/
    foundation.py                # Foundation dataclass, open_foundation(), import_seed_data()
    core/context.py              # TENANT_ID_PATTERN, TenantScope
    core/clock.py                # Clock(ABC), SystemClock, FrozenClock
    db/
      records.py                 # TenantRecord base + the example record
      tables.py                  # metadata, UtcDateTime, one Table per record and memory store
      engine.py                  # build_database_url(), open_database()
      repository.py              # RecordRepository(ABC), InMemory*, Sql*
      csv_import.py              # load_csv_records(), import_csv_records(), ImportReport
    rag/
      contracts.py               # DocumentEntry, DocumentChunk, VectorQuery, ScoredChunk, reports
      embedder.py                # BaseEmbedder(ABC), HashingEmbedder, PydanticAIEmbedder
      vector_store.py            # VectorStore(ABC), InMemoryVectorStore, SqlVectorStore
      ingestion.py               # load_document_index(), split_document_text(), ingest_documents()
      retriever.py               # Retriever.search_chunks()
    memory/
      preferences.py             # MemoryPreference, PreferenceMemory
      conversation.py            # ConversationStore(ABC), InMemory*, Sql*
    tools/
      base.py                    # ToolSpec, ToolContext, BaseTool(ABC)
      <domain>.py                # The example read-only tool
    mcp/
      server.py                  # build_mcp_server(), register_mcp_tool(), build_tool_signature()
      <domain>_server.py         # Runnable stdio server: python -m app.mcp.<domain>_server
      client.py                  # load_mcp_catalog(), open_role_toolsets()
  tests/
    synthetic.py                 # Writes sample rows, preferences, and a two-tenant corpus into tmp_path
    test_db.py  test_rag.py  test_memory.py  test_mcp.py  test_foundation.py
  data/                          # Ignored (template): app.db and MCP server logs
```

## Database: SQLite now, PostgreSQL by URL later

- **Stack:** SQLAlchemy 2 async **Core** (`Table`, not the ORM) with `aiosqlite`. `<PREFIX>_DATABASE_URL` is a `SecretStr`, excluded from `repr`. When it is blank, the URL is `sqlite+aiosqlite:///<project>/backend/data/app.db` (absolute), the template's SQLite location. `build_database_url(location.state_dir, url)`. A PostgreSQL URL later changes only the driver dependency.
- **`open_database(url)`:**
  - creates the engine, creating the SQLite parent directory first;
  - sets `PRAGMA foreign_keys=ON` through a connect event, because SQLite otherwise ignores foreign keys;
  - runs `metadata.create_all`, then disposes of the engine on exit;
  - maps a bad URL (`ArgumentError`, `ImportError`, `ValueError`) to `ConfigurationError("invalid_database_url")`.
- **`UtcDateTime` TypeDecorator:** stores UTC ISO text, rejects naive datetimes, and reads back aware UTC. SQLite has no timezone type, and without this, comparisons silently go wrong.
- **Records:** `TenantRecord(Contract)` has `key_field: ClassVar[str]`, `tenant_id`, and a `record_key` property. Put cross-field invariants in `model_validator`s on the record, so the database, CSV, and fakes all enforce them. Cashflow's invoice checks `total = subtotal + tax`, `balance = total - paid`, and `due_date >= issue_date`.
- **`RecordRepository[RecordT]`:**
  - `save_records(records) -> int`: atomic; upserts by tenant and key. The SQL version updates first, then inserts if `rowcount == 0`, and maps `IntegrityError` to `StorageError("integrity_violation")`.
  - `get_record(scope, key)`: raises `RecordNotFoundError`.
  - `list_records(scope, *, limit)`: `limit` is at most 500.
- **CSV import:**
  - The header must name exactly the model's fields, each once. Column order is free because rows are read by name; write `tenant_id` first by convention.
  - Empty cells become `None`. Validate with `model_validate(row, strict=False)`, because CSV cells are strings; `Contract` stays strict everywhere else.
  - Collect every invalid row before raising.
  - **All or nothing:** load and validate every file before writing any.
  - The importer is the one step that reads `data/raw/`. The database under `backend/data/` is its processed output.

## RAG: embeddings, vector store, ingestion, retrieval

- **Embedding profiles** live in `models.toml`, separate from chat profiles: `provider` (`fixture` or `openai`), `model_id`, `dimensions` (8–4096), `timeout_seconds`, and `max_batch_size`.
  - `index_version = f"{provider}:{model_id}:{dimensions}"` is stored with every chunk, so changing the model or its dimensions can never mix vectors.
  - Fixture mode always uses the `fixture` profile; live mode uses `default_embedding_profile`.
  - **Anthropic has no embeddings API.** Hosted embeddings use the OpenAI key, `<PREFIX>_OPENAI_API_KEY`.
- **`BaseEmbedder(ABC)`:** `embed_documents(texts)` batches by `max_batch_size` and sums token usage; the total is `None` if any batch count is unknown, never a fabricated zero. `embed_query(text)`. Both reject blank input and verify the vector count and dimensions. Implementations define only `_embed_texts(texts, kind)`.
  - `HashingEmbedder`: offline and deterministic. It hashes words (blake2b) into signed buckets and L2-normalizes. Do not use Pydantic AI's `TestEmbeddingModel`: it returns identical vectors, so it cannot test ranking. The hashing embedder matches words, not meaning, and unrelated words can cancel in a shared bucket. Never use it to judge retrieval quality.
  - `PydanticAIEmbedder`: wraps `Embedder(OpenAIEmbeddingModel(model_id, provider=OpenAIProvider(openai_client=client)), instrument=False)` with `EmbeddingSettings(dimensions=...)`. `bootstrap.open_embedder` opens `AsyncOpenAI(max_retries=0, timeout=profile.timeout_seconds)`. Map `ModelHTTPError` through the shared status classifier to `EmbeddingError("<code>: ...")`; map `ModelAPIError` or `TimeoutError` to `network`.
- **`VectorStore(ABC)`:**
  - `replace_document_chunks(scope, document_id, chunks)`: atomic within one index version.
  - `list_nearest_chunks(scope, VectorQuery)`: the limit is at most 20.
  - `SqlVectorStore` stores vectors as JSON. It selects by tenant and index version, then ranks by exact cosine in Python, sorting by `(-score, chunk_id)` so ties are deterministic.
- **Document index:** a versioned `index.json` beside the raw documents. `DocumentEntry` holds `document_id`, `tenant_id`, `title`, `path`, `sha256`, and `trust_level: Literal["untrusted_content"]`, plus domain metadata as the project needs it.
  - Ingestion rejects duplicate IDs.
  - A document's path must stay inside `documents/<tenant_id>/`, otherwise `invalid_document_path`.
  - The bytes must match `sha256`, otherwise `document_hash_mismatch`.
  - Retrieved text is evidence, never instructions.
- **`ingest_documents(root, embedder, store)`:** validates and splits every document first (paragraph merge up to 800 characters, deterministic `chunk_id`), embeds all chunks in batches, then replaces chunks per document.
- **`Retriever(embedder, store).search_chunks(scope, RetrievalQuery)`:** the query text is at most 2,000 characters; the limit defaults to 5.

## Memory

- **Preferences:** `MemoryPreference(TenantRecord)` has `status` (`approved`, `pending`, or `revoked`), a validity window, and an optional subject key. `PreferenceMemory(repository, clock).list_active_preferences(scope, *, <subject>=None)` returns tenant-wide approved preferences plus that subject's, active at `clock.get_current_time()`. Only approved preferences reach a prompt. Facts are read from their authoritative records, never from memory.
- **Conversation:** `ConversationStore(ABC)`:
  - `save_messages(scope, thread_id, messages)` creates the thread for that tenant on first write; another tenant gets `AccessDeniedError`.
  - `load_messages(scope, thread_id, *, limit)` returns the last N messages (at most 200), oldest first. An unknown thread returns `[]`.
  - Messages are Pydantic AI `ModelMessage`s, serialized with `ModelMessagesTypeAdapter` in JSON mode, so `agent.run(message_history=...)` round-trips them. Test this with a real `Agent` on `TestModel`.
- **`Clock(ABC)`:** `SystemClock` and `FrozenClock(frozen_at)`. The frozen clock rejects naive datetimes. Inject the clock; never call `datetime.now()` in logic.

## Tools and MCP

Tools are plain Python classes first; MCP is one way to serve them.

- **`BaseTool[ArgumentsT, ResultT](ABC)`** takes a `ToolSpec` (name, version, description, `is_read_only`, `timeout_seconds` up to 30), the argument type, and the result type. `call_tool(context, arguments)`:
  1. validates the arguments with `strict=False`, because MCP delivers JSON, raising `ToolAccessError("invalid_arguments: <name>")`;
  2. runs `_run_tool` under `asyncio.timeout`, raising `ToolAccessError("timeout: <name>")`.
  The result model returns only what the model needs; cashflow's customer summary omits email.
- **Server (`mcp` 2.x):**
  - Use `mcp.server.mcpserver.MCPServer`. It was `FastMCP` in 1.x, and its fields are now snake_case, e.g. `read_only_hint`.
  - `register_mcp_tool` wraps `call_tool`. It turns `<Package>Error` into `ToolError(str(error))` and returns `model_dump(mode="json")`.
  - It sets the wrapper's `__signature__` from the argument model, using `Annotated[field.annotation, field]`. This keeps descriptions and constraints in the advertised schema, so no schema is written by hand. Pass `ToolAnnotations(read_only_hint=...)`.
  - The server module parses `--project-root` and `--tenant`, loads settings in fixture mode, opens the database, and runs `run_stdio_async()`.
- **Catalog (`config/mcp.toml`)** is validated into `MCPCatalog`. A server's module must match `^app(\.[a-z_]+)+$`: only this package's modules can be launched, never arbitrary commands. Every role references known servers and tools.
- **Client:** `open_role_toolsets(location, catalog, *, role, scope, database_url)` yields one Pydantic AI toolset per server, each `.filtered()` to the role's allowlist.
  - It builds `MCPToolset(StdioTransport(sys.executable, ["-m", module, "--project-root", root, "--tenant", tenant], env=..., cwd=backend_root, keep_alive=False, log_file=state_dir / "mcp-<server>.log"))`. The `backend/` working directory makes `-m app...` importable even without an installed package.
  - **`keep_alive=False`** is required, or the server outlives the toolset.
  - **`log_file`** is required: the default is `sys.stderr`, which fails under pytest's output capture and mixes server logs into CLI output.
  - **Child environment:** only `PATH`, `<PREFIX>_DATABASE_URL`, `<PREFIX>_MODEL_MODE=fixture`, and any set `PLATFORM_VARIABLES`. That tuple is `("OPENSSL_armcap",)`, nonsecret settings the child needs to start on this host; without it, MCP servers crash inside the Docker image on Apple M4. The child gets no API keys and no inherited prefixed variables, and a test asserts the exact key set.
  - **Fail closed:** after connecting, compare `list_tools()` with the catalog. A mismatch raises `unexpected_tool_catalog`; a failed start raises `mcp_unavailable`.

## Startup composition: `foundation.py`

`open_foundation(location, settings, *, clock=None)` is an async context manager, the one place startup wires everything. It:
1. loads the MCP catalog and the embedding profile, then resolves the database URL;
2. opens the database and the embedder;
3. yields a frozen `Foundation` dataclass holding `engine`, `database_url` (`field(repr=False)`), `clock`, the record repositories, preferences, conversations, `embedder`, `vector_store`, `retriever`, and `mcp_catalog`.

`build_foundation(...)` is the pure assembly step tests call. `import_seed_data(foundation, directory)` loads and validates every source before saving any, and returns one `ImportReport` per table.

## CLI additions

| Command | Does | Live? |
|---|---|---|
| `config-check` | Also prints `embedding_index`, `database` (`configured_url` or the SQLite path, never the URL), `mcp_servers`, and `tool_roles` | No |
| `data-import --directory data/raw/<source>/<date>` | Validates all CSVs, then upserts them; rerunnable | No |
| `index-documents --directory data/raw/documents/<date>` | Ingests the listed documents for the active index version | `--live` |
| `search --tenant T --query Q` | Top chunks with `document_id`, `chunk_id`, `score`, and a 160-character preview | `--live` |
| `mcp-check --tenant T` | Starts each role's servers and checks their tool catalogs | No |

Validate `--tenant` and `--query` through `TenantScope` and `RetrievalQuery` before opening anything, and report only the field names on failure (`invalid_option: invalid tenant_id`). A raw `ValidationError` traceback is a bug. `--live` belongs only to the commands marked in the table.

## Tests

The conftest from [foundation.md](foundation.md) still blocks `socket.connect`. Every test uses a temporary SQLite file or the in-memory fakes, and writes its own small CSV and document files into `tmp_path`. Nothing is read from `data/`.

- **`test_db.py`:**
  - The repository contract runs over the fake and SQL implementations: round trip, upsert, tenant isolation, missing key, and limit bounds.
  - A bad composite foreign key raises `integrity_violation`.
  - A naive datetime is rejected.
  - CSV imports report header, row, and type errors with line numbers and no values.
  - A failure in a later file leaves the database empty.
  - A bad URL raises a configuration error.
- **`test_rag.py`:**
  - The hashing embedder is deterministic and ranks overlapping text higher.
  - Batching and token sums work, and unknown usage stays `None`.
  - Wrong vector counts or dimensions are rejected.
  - The vector store contract runs over both implementations: one tenant's search never returns another tenant's chunk, and versions stay separate.
  - Path escapes and hash mismatches are rejected.
  - The OpenAI embedder runs through `httpx.MockTransport`: request shape, requested dimensions, and error codes by status.
- **`test_memory.py`:**
  - Preference windows, status, and subject filtering work under `FrozenClock`.
  - The conversation contract runs over both implementations, including the last-N order and another tenant's `AccessDeniedError`.
  - A real `Agent` on `TestModel` round-trips its history.
- **`test_mcp.py`:**
  - A tool validates its arguments and deadline.
  - The advertised schema keeps descriptions and limits.
  - The catalog rejects foreign modules and unknown tools.
  - A **real stdio subprocess** serves the tools, and an agent scripted with `FunctionModel` calls one through `open_role_toolsets`.
  - A server serves only its launch tenant.
  - A role sees only its allowlist, and a catalog mismatch fails closed.
  - After the suite, check by hand that no server processes remain (`ps -ax | grep app.mcp`); cashflow verified this manually, not in a test.
- **`test_foundation.py`:**
  - `open_foundation` composes offline on an empty database.
  - Live embeddings without the OpenAI key fail, naming the variable.
  - The CLI runs import, index, search, and `mcp-check` under output capture.
  - Options outside their command are rejected, including invalid tenant and query values.
  - A configured database URL is never printed.

**Live check:** `index-documents --live` then `search --live`, run only when the user authorizes hosted embeddings. Documents at initialization are the test's own synthetic text, or a single synthetic file the user approves, never client data. Report chunks, tokens, and whether results stayed in the tenant. That is a connection check, not a retrieval-quality result.

## Shortcuts to flag in the README

State each of these as a deliberate first slice:
- `create_all` instead of migrations.
- JSON vectors with exact Python cosine instead of pgvector.
- The MCP tenant is fixed at server launch instead of authenticated per request.
- Tools may filter in Python.
- Preference reads cap at 500 rows.
- A truncated history window can begin with an orphaned tool result.
- The hashing embedder is lexical only.

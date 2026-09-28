# `core/` — settings, errors, tenant scope, and time

The small set of things every other package needs: where the project lives and how it is configured (`settings.py`), how failures are reported (`errors.py`), on whose behalf a read runs (`context.py`), and what time it is (`clock.py`). Nothing here talks to a model, a database, or the network.

## Files

### `settings.py` — configuration

**`ProjectLocation`**: the project root, passed in explicitly and never discovered by walking up directories. Its properties give the fixed layout:

| Property | Path | Holds |
|---|---|---|
| `root` | project root | `.env`, `data/`, `backend/` |
| `backend_root` | `backend/` | working directory for MCP server processes |
| `config_dir` | `backend/config/` | versioned TOML |
| `env_file` | `.env` | the only dotenv file read |
| `data_root` | `data/` | input data |
| `state_dir` | `backend/data/` | ignored: `app.db`, MCP logs |

`DEFAULT_PROJECT_ROOT` is computed from this file's location (`settings.py` → `core` → `app` → `backend` → root). Docker keeps the same layout so it stays correct in the container.

**`Settings`**: the validated runtime settings (a pydantic-settings class). Every field maps to a `TEMPLATE_<FIELD>` variable:

| Field | Variable | Default | Notes |
|---|---|---|---|
| `env` | `TEMPLATE_ENV` | `local` | `local` or `test`; selects `config/<env>.toml` |
| `model_mode` | `TEMPLATE_MODEL_MODE` | `fixture` | `fixture` or `live` |
| `external_actions_enabled` | `TEMPLATE_EXTERNAL_ACTIONS_ENABLED` | `False` | Typed `Literal[False]`: only `false` is accepted, so it cannot be switched on |
| `openai_api_key`, `anthropic_api_key` | `TEMPLATE_OPENAI_API_KEY`, `TEMPLATE_ANTHROPIC_API_KEY` | none | `SecretStr`, `repr=False` |
| `llm_provider` | `TEMPLATE_LLM_PROVIDER` | none | Optional vendor override |
| `llm_model` | `TEMPLATE_LLM_MODEL` | none | Optional model ID override |
| `database_url` | `TEMPLATE_DATABASE_URL` | none (SQLite in `backend/data/app.db`) | `SecretStr`: a URL may embed a password |

Why these settings choices: `env_ignore_empty=True` makes `KEY=` in `.env` mean "unset", not an empty key. `hide_input_in_errors=True` stops a validation error from echoing the rejected value, which could be a key. `extra="ignore"` lets `.env` hold variables for other tools.

**Precedence**, lowest to highest: `config/default.toml` → `config/<env>.toml` → `.env` → process environment. `settings_customise_sources` enforces this, because pydantic-settings would otherwise rank the TOML (passed as constructor arguments) highest.

**Loaders**:

- `load_settings(location, *, execution_mode=None)` merges the sources and returns `Settings`. An unknown key in TOML fails (`unknown_setting`). `execution_mode` overrides the mode for one invocation; this is how the CLI keeps `--live` as the only way into live mode. Live mode without any key fails with `missing_credentials`.
- `load_model_profile(location, settings, prompt=None, *, vendor=None)` resolves which chat model an agent uses, from `config/models.toml` (`ModelCatalog`). In fixture mode it always returns `profiles.fixture`. In live mode, lowest to highest priority: `default_profile` → `roles[<agent>]` → the prompt YAML's `model_profile` → the YAML's `model` → `TEMPLATE_LLM_MODEL`. A vendor (`--provider` or `TEMPLATE_LLM_PROVIDER`) replaces the role selection with `vendor_profiles[vendor]` and drops the YAML `model`, which belongs to the default vendor. An explicit `--provider` also ignores `TEMPLATE_LLM_MODEL`, so the probe uses exactly that vendor's catalog profile.
- `load_embedding_profile(location, settings)` returns `embedding_profiles.fixture` offline, or `default_embedding_profile` live.

Every profile name the catalog or prompt mentions is checked first (`_validate_profile_references`), so a typo fails in every mode, not only the mode that uses it. A fixture profile in live mode, or the reverse, is refused (`_require_mode_compatible`).

`API_KEY_VARIABLES` maps each vendor to its variable **name**; it is used in messages and in `config-check`, and never holds values.

### `errors.py` — the exception hierarchy

Every known failure is an `AppError` subclass whose message starts with a stable code, for example `storage_failed: could not save records`. Messages never contain keys, provider response bodies, or row values, so a boundary can print `str(error)` safely.

| Class | Raised when |
|---|---|
| `ConfigurationError` | Settings, catalogs, prompts, or keys are missing or invalid |
| `ProviderError` | A model request failed (`timeout`, `rate_limit`, `authentication`, …) |
| `AgentInputError` | A request violates the agent's input schema |
| `AgentOutputError` | A model response breaks the output contract or stops early |
| `StorageError` | A database operation failed |
| `RecordNotFoundError` (also a `LookupError`) | The tenant has no such record; another tenant's record looks identical to a missing one |
| `InvalidQueryError` (also a `ValueError`) | An unbounded or malformed read, such as `limit=0` |
| `DataImportError` | A CSV, preferences file, or document index is invalid; nothing was written |
| `EmbeddingError` | An embedding request failed or returned the wrong shape |
| `AccessDeniedError` (also a `PermissionError`) | A tenant touched a resource it does not own |
| `ToolAccessError` | A tool call was denied, invalid, timed out, or a server advertised unexpected tools |

Only the boundaries catch `AppError`: `run_cli`, the HTTP routes, and the MCP server. Inside the application, let errors propagate.

### `context.py` — the tenant scope

`TenantScope(tenant_id=...)` names the tenant a read or write runs for; `TENANT_ID_PATTERN` (`^tenant_[a-z0-9_]+$`) restricts the IDs. Every repository, vector store, conversation store, and tool takes a scope. It is built by the application (today the CLI and tests; later, authentication from a verified session). **A model never supplies it**, so a prompt injection cannot ask for another tenant's data.

### `clock.py` — the time source

`Clock` is an ABC with one method, `get_current_time()`, returning an aware UTC datetime. `SystemClock` reads the OS time; `FrozenClock(frozen_at)` returns a fixed instant for tests (it rejects naive datetimes). Code that needs "now", such as preference expiry, receives a `Clock` instead of calling `datetime.now()`, so tests about expiry are deterministic.

## How it connects

- `settings.py` imports `llm/contracts.py` (the profile contracts) and `llm/prompts.py` (to read a prompt's model selection).
- Every other package imports `errors.py`; storage, retrieval, memory, and tools import `context.py`.
- `main.py`, `cli.py`, `foundation.py`, `bootstrap.py`, and `mcp/examples_server.py` call the loaders.

## How to use

```python
from app.core.settings import (
    DEFAULT_PROJECT_ROOT,
    ProjectLocation,
    load_embedding_profile,
    load_model_profile,
    load_settings,
)

location = ProjectLocation(root=DEFAULT_PROJECT_ROOT)
settings = load_settings(location, execution_mode="fixture")
profile = load_model_profile(location, settings)  # profiles.fixture
embedding = load_embedding_profile(location, settings)  # embedding_profiles.fixture
print(settings.model_mode, profile.model_id, embedding.index_version)
```

From the shell, `template-cli config-check` does the same and prints the result as JSON.

## How to extend

- **A new setting:** add a field to `Settings` with a `Field(description=...)`, give it a default in `config/default.toml` if it is not secret, and document the `TEMPLATE_` variable in `.env.example`. A secret must be `SecretStr` with `repr=False`, and must never appear in TOML.
- **A new error:** subclass `AppError` (and a builtin such as `LookupError` when callers may catch that), document when it is raised, and start every message with a fixed code.
- **A new model profile:** add it to `config/models.toml`; no code change is needed.

## Tests

`tests/test_settings.py` covers precedence, unknown keys, secret handling, and profile resolution. `FrozenClock` is used in `tests/test_memory.py`.

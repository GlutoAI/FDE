# `llm/` — the model layer

Everything between an agent and a model vendor: the data contracts, the `ModelProvider` boundary that hides vendor differences, safe prompt loading, and the builder that turns those into a Pydantic AI runtime. Agents in [`agents/`](../agents/README.md) depend only on this package, never on a vendor SDK.

## Files

### `contracts.py` — the data contracts

**`Contract`** is the base of almost every data object in the application: a Pydantic model with `frozen=True` (immutable), `extra="forbid"` (unknown fields are an error), and `strict=True` (no silent type coercion, so `"42"` is not accepted as `42`). It lives here for historical reasons, but `core/`, `db/`, `rag/`, `tools/`, and `mcp/` all build on it.

| Contract | Purpose |
|---|---|
| `ProviderName`, `LiveProviderName` | `fixture`/`openai`/`anthropic`, and the two hosted ones |
| `ModelProfile` | One entry of `[profiles.*]` in `config/models.toml`: provider, `model_id`, `timeout_seconds` (≤ 60), `max_output_tokens` (16–256), optional `reasoning_effort` |
| `EmbeddingProfile` | One entry of `[embedding_profiles.*]`: provider, `model_id`, `dimensions`, timeout, `max_batch_size`. Its `index_version` property (`provider:model:dimensions`) is stored with every vector |
| `AgentResult[OutputT]` | What `run_agent` returns: the validated `output` plus provenance: `provider`, `model_id`, `prompt_version`, `prompt_sha256`, `input_tokens`, `output_tokens` |
| `PromptReference` | A path-safe `(agent, version)` pair naming a YAML file |
| `PromptTemplate` | The validated YAML content: `agent`, `version`, `system`, `user`, optional `model_profile` and `model` |
| `LoadedPrompt` | A `PromptTemplate` plus the SHA-256 of the exact file bytes |

Why provenance lives in `AgentResult` and not in the output schema: the model writes `output`; the application fills in everything else after the call. The model therefore cannot claim to be a different model or prompt version.

### `provider.py` — the vendor boundary

`ModelProvider` is an ABC with four methods. Each vendor implements them in [`providers/`](providers/README.md):

| Method | Returns |
|---|---|
| `get_model()` | The Pydantic AI `Model`, already built by `bootstrap.py`; no network |
| `build_model_settings(profile)` | Request limits (`max_tokens`, `timeout`) plus vendor-specific keys |
| `build_output_spec(output_type)` | `NativeOutput` (JSON-schema output) where supported, otherwise `ToolOutput` |
| `classify_sdk_error(error)` | `timeout`, `network`, `invalid_response`, or `None` if the error is not this SDK's |

The provider never opens an SDK client; `bootstrap.py` owns client lifetimes and passes the model in. That keeps providers trivially testable.

### `runtime.py` — building the runtime and normalizing errors

- **`build_agent_runtime(provider, prompt, profile, *, input_type, output_type)`** returns a typed Pydantic AI `Agent`: the model, the output spec, the system prompt as `instructions`, the settings, and **`retries=0`**, so an invalid response fails loudly and costs exactly one call instead of being silently re-asked.
- **`normalize_model_errors(provider)`** is a context manager wrapped around the model call. It translates every failure into a safe `AppError` whose message is a fixed code:

  | Raised inside | Becomes |
  |---|---|
  | `TimeoutError` | `ProviderError("timeout: …")` |
  | `ModelHTTPError` | `ProviderError("<code>: …")` via `classify_http_status` |
  | `ModelAPIError` | `ProviderError("<sdk code or network>: …")` |
  | `UserError` | `ConfigurationError("unsupported_model_configuration: …")` |
  | `UnexpectedModelBehavior`, `UsageLimitExceeded`, `ValidationError` | `AgentOutputError("invalid_output: …")` |
  | `AttributeError`, `TypeError` (malformed 200 response) | `ProviderError("invalid_response: …")` |
  | Another exception the provider recognizes | `ProviderError` |
  | Anything else | Re-raised unchanged; it is a bug |

  The original exception, which may contain the response body, is kept only as `__cause__` and never appears in the message.
- **`classify_http_status(status, body)`** maps 401 → `authentication`, 403 → `permission`, 404 → `model_unavailable`, 400 → `invalid_request`, 429 → `rate_limit` (or `quota` when the body's `code` is `insufficient_quota`), and anything else to `provider_error`. It reads only the body's `code` field, never its message. `rag/embedder.py` reuses it.

### `prompts.py` — safe prompt loading

`load_prompt(reference)` reads `app/prompts/<agent>/v<version>.yaml` from the installed package with `importlib.resources`, parses it with `yaml.safe_load` (no code execution), validates it as a `PromptTemplate`, checks that the file's own `agent` and `version` match the reference, and returns a `LoadedPrompt` with the SHA-256 of its bytes. Because `PromptReference.agent` must match `^[a-z][a-z0-9_]*$`, a reference can never traverse to a parent directory.

## How it connects

```text
config/models.toml ──(core/settings.py)──> ModelProfile ─┐
prompts/<agent>/v1.yaml ──(prompts.py)───> LoadedPrompt ─┼─> build_agent_runtime ──> Agent ──> BaseAgent.run_agent
bootstrap.py ──(opens SDK client)────────> ModelProvider ┘                                    (inside normalize_model_errors)
```

## How to use

You rarely call this package directly; `bootstrap.py` does. To build an agent by hand, for example in a test:

```python
from pydantic_ai.models.test import TestModel

from app.bootstrap import build_connection_agent
from app.llm.contracts import ModelProfile, PromptReference
from app.llm.prompts import load_prompt
from app.llm.providers.fixture import FixtureModelProvider

prompt = load_prompt(PromptReference(agent="connection", version=1))
profile = ModelProfile(
    provider="fixture", model_id="fixture", timeout_seconds=2, max_output_tokens=128
)
model = TestModel(
    custom_output_text='{"status":"ok","marker":"CONNECTION_OK"}',
    profile={"supports_json_schema_output": True},
)
agent = build_connection_agent(FixtureModelProvider(model), prompt, profile)
```

## How to extend

- **A new vendor:** see [`providers/README.md`](providers/README.md).
- **A new contract field:** add it with a `Field(description=...)`. Contracts are strict, so every producer must then supply it.
- **A new error mapping:** add a branch to `normalize_model_errors` **before** any broader class it subclasses (`ModelHTTPError` subclasses `ModelAPIError`, so its branch comes first).

## Tests

`tests/test_providers.py` covers the providers, their settings, output modes, and error classification. `tests/test_agents.py` covers the runtime through the connection agent.

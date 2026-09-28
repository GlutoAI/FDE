# `llm/providers/` — one `ModelProvider` per vendor

Each file implements the [`ModelProvider`](../README.md#providerpy--the-vendor-boundary) ABC for one vendor. They are deliberately thin: they wrap a Pydantic AI model that `bootstrap.py` already built, and translate the shared profile into that vendor's settings, output mode, and SDK error codes. None of them opens a client or makes a request.

## Files

### `fixture.py` — `FixtureModelProvider`

The offline provider used by default runs, the `/diagnostics/connection` route, and tests. It wraps Pydantic AI's `TestModel`, which produces schema-valid output (or a scripted `custom_output_text`) without any network access.

- Settings: only the shared `max_tokens` and `timeout`.
- Output: always `NativeOutput`.
- `classify_sdk_error`: always `None`; it has no SDK.

### `openai.py` — `OpenAIModelProvider`

Wraps `OpenAIResponsesModel` (the OpenAI Responses API).

- Settings: `max_tokens`, `timeout`, and **`openai_store=False`**, which keeps prompts and responses out of OpenAI's stored-response history. When the profile sets `reasoning_effort`, it is passed as `openai_reasoning_effort`.
- Output: `NativeOutput` (JSON-schema structured output).
- Errors: `APITimeoutError` → `timeout`, `APIConnectionError` → `network`, `APIResponseValidationError` → `invalid_response`.

### `anthropic.py` — `AnthropicModelProvider`

Wraps `AnthropicModel` (the Messages API).

- Settings: `max_tokens` and `timeout`. A profile with `reasoning_effort` raises `ConfigurationError`, because there is no mapping to Anthropic's settings yet. This fails at startup rather than silently ignoring the setting.
- Output: `NativeOutput` when the model's profile reports `supports_json_schema_output`, otherwise `ToolOutput`, because older Claude models return structured output through a tool call.
- Errors: the same three SDK classes as OpenAI, from the `anthropic` package.

## How it connects

`bootstrap.open_model_provider` chooses the class from `profile.provider`, opens the SDK client with a pinned base URL and `max_retries=0`, builds the Pydantic AI model on it, and yields the provider. `llm/runtime.py` then calls `build_model_settings` and `build_output_spec` when building the runtime, and `classify_sdk_error` when translating errors.

## How to add a vendor

1. Add the vendor name to `ProviderName` and `LiveProviderName` in `llm/contracts.py`, and its key variable to `API_KEY_VARIABLES` and a `SecretStr` field to `Settings` in `core/settings.py`.
2. Create `providers/<vendor>.py` with a subclass implementing the four methods. Map only settings the vendor honors; raise `ConfigurationError` for anything it cannot honor rather than dropping it.
3. Add a branch in `bootstrap.open_model_provider` that opens the vendor's async client (pinned base URL, `max_retries=0`, the profile's timeout) inside `async with`, so it is always closed.
4. Add profiles to `config/models.toml` (`[profiles.*]` and `[vendor_profiles]`).
5. Add tests in `tests/test_providers.py`: settings mapping, output mode, and error classification, all offline.

## Tests

`tests/test_providers.py`.

# `prompts/connection/` — the connection diagnostic prompt

## Files

### `v1.yaml`

The prompt of the [connection agent](../../agents/connection/README.md), the smallest possible real model call: it proves that credentials, the model ID, structured output, and error handling all work, without sending any business data.

- `system` tells the model to return a JSON object matching the output schema, with `status` `"ok"` and `marker` equal to the input's `expected_marker`, and nothing else.
- `user` is a fixed synthetic message; the agent appends the validated `ConnectionInput` as JSON after it.
- `model_profile: null` and `model: null`: the model comes from `config/models.toml` (`roles.connection`, then `default_profile`). Set `model` to try a different model ID for this agent only; `TEMPLATE_LLM_MODEL` still takes precedence.

## How it is used

`bootstrap.create_connection_agent` loads it with `PromptReference(agent="connection", version=1)`. It runs:

- offline, through the fixture model, with `template-cli smoke` and `POST /diagnostics/connection`;
- against a hosted model only with `template-cli smoke --live [--provider openai|anthropic]`, which sends exactly one request.

## Changing it

Do not edit `v1.yaml` once results exist. Add `v2.yaml` with `version: 2`, and change the `PromptReference` in `bootstrap.create_connection_agent` and in `core/settings.load_model_profile` (its default prompt) to version 2.

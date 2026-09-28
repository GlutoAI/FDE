# `agents/connection/` — the connection diagnostic agent

A no-tool agent that proves the whole model path works end to end, including configuration, credentials, the model ID, structured output, validation, and provenance, while sending no business data. It is the template's reference implementation of [`BaseAgent`](../README.md): every new agent follows the same two-file shape.

## Files

### `models.py` — the contracts

- **`ConnectionInput`** has one field, `expected_marker: Literal["CONNECTION_OK"]`, with that value as the default. Because the type is a literal, arbitrary data cannot be sent through the probe.
- **`ConnectionOutput`** has `status: Literal["ok"]` and `marker: Literal["CONNECTION_OK"]`. This is the schema Pydantic AI sends to the model, and it validates the response against it. A wrong status, a missing field, an extra field, or a wrong type all fail validation.

Keeping contracts in their own file, beside the agent, means callers (the CLI and the router) can import the types without importing the agent or its dependencies.

### `agent.py` — `ConnectionAgent`

`ConnectionAgent(BaseAgent[ConnectionInput, ConnectionOutput])` implements only `_validate_output`: the returned `marker` must equal the request's `expected_marker`, otherwise `AgentOutputError("unexpected_output: …")`. With today's literal types the schema already guarantees this; the check stays so the agent remains correct if the input type is ever widened. It also shows where input-dependent rules belong.

## How it is built and run

`bootstrap.create_connection_agent(location, settings, vendor=None)` loads [`prompts/connection/v1.yaml`](../../prompts/connection/README.md), resolves the profile, opens the provider, and yields the agent:

| Caller | Mode | Cost |
|---|---|---|
| `template-cli smoke` | Fixture | None |
| `POST /diagnostics/connection` | Always fixture, whatever the settings say | None |
| `template-cli smoke --live [--provider openai\|anthropic]` | Hosted | Exactly one request, at most `max_output_tokens` output tokens |

```bash
cd backend
.venv/bin/template-cli smoke
# {"mode": "fixture", "elapsed_seconds": ..., "status": "ok", "output": {"status": "ok", "marker": "CONNECTION_OK"}, "provider": "fixture", ...}
```

## Tests

`tests/test_agents.py` covers valid output, rejection of each kind of invalid output, and revalidation of constructed input. `tests/test_bootstrap.py` covers composition and profile selection.

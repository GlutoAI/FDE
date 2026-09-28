# `tools/` — typed, bounded tools an agent may call

A tool is a deterministic function a model can ask to run, such as "look up record REC-1001". This package defines the tool contract and ships one read-only example. Tools reach models through MCP (see [`mcp/`](../mcp/README.md)), but they know nothing about MCP: the same `BaseTool` can be called directly in a test.

**Model judgement vs deterministic code:** the model chooses **which** tool and **which arguments**. Everything after that choice is deterministic: argument validation, the deadline, the tenant restriction, and the shape of the result.

## Files

### `base.py` — the tool contract

- **`ToolSpec`**: what the model sees and how the tool may run. It has `name` (snake_case, which the model calls), `version` (bump it when arguments or results change), `description` (shown to the model, so write it for the model), `is_read_only`, and `timeout_seconds` (≤ 30).
- **`ToolContext`**: server-side facts about the call. Today that is the `scope` (`TenantScope`). **Models cannot set any of it**: the tenant is fixed where the server is launched, never taken from arguments.
- **`BaseTool[ArgumentsT, ResultT]`**: the ABC. The constructor stores `spec`, `arguments_type`, and `result_type`.
  - `call_tool(context, arguments)` is the fixed sequence. It validates the raw JSON arguments against `arguments_type` (non-strict, because a date arrives as a string in JSON), raising `ToolAccessError("invalid_arguments: <tool>")` on failure. It then runs `_run_tool` inside `asyncio.timeout(spec.timeout_seconds)`, raising `ToolAccessError("timeout: …")` if the deadline passes.
  - `_run_tool(context, arguments)` is the only method a tool implements: its own logic, for `context.scope` only, returning a `result_type` instance.

### `examples.py` — the example read-only tool

- `ExampleRecordLookup` is the arguments: one `record_id`, validated against `RECORD_KEY_PATTERN`.
- `ExampleRecordSummary` is the result: `record_id`, `name`, `category`, `amount_cents`, `opened_on` (ISO text), and `is_open`.
- `GetExampleRecordTool(repository)` is `get_example_record`, read-only, with a 5-second deadline. It reads the record through `repository.get_record(context.scope, …)`.

Two design choices worth copying:

1. **The result omits `owner_id`.** A tool returns only what the model needs to reason about, never identity it does not need.
2. **Another tenant's record looks exactly like a missing one** (`RecordNotFoundError`), so the model cannot learn that it exists.

## How it connects

```text
config/mcp.toml ──> mcp/client.py (starts server, filters tools per role) ──> agent's toolsets
                                           │ stdio
mcp/examples_server.py ──> build_example_tools(engine) ──> mcp/server.py (registers each BaseTool)
                                                                   │
                                                  tool.call_tool(ToolContext(scope=launch tenant), args)
```

## How to use

Call a tool directly, as a test does:

```python
from app.core.context import TenantScope
from app.db.records import ExampleRecord
from app.db.repository import RecordRepository
from app.tools.base import ToolContext
from app.tools.examples import ExampleRecordSummary, GetExampleRecordTool


async def lookup(repository: RecordRepository[ExampleRecord]) -> ExampleRecordSummary:
    tool = GetExampleRecordTool(repository)
    context = ToolContext(scope=TenantScope(tenant_id="tenant_alpha"))
    return await tool.call_tool(context, {"record_id": "REC-1001"})
```

From the shell, `template-cli mcp-check --tenant tenant_alpha` starts the MCP server and verifies it advertises exactly the approved tools.

## Tutorial: adding a tool

1. **Contracts.** Define an arguments `Contract` and a result `Contract`, with a `Field(description=...)` on every field. The argument descriptions and limits become the JSON schema the model sees.
2. **The tool.** Subclass `BaseTool[Args, Result]`. In `__init__`, receive collaborators such as repositories (never build them), and pass a `ToolSpec` to `super().__init__`. Implement `_run_tool`: read or write **only** `context.scope`'s data, and raise an `AppError` subclass with a safe message for every expected failure.
3. **Register it** in the server's `build_example_tools` (or your own server module; see [`mcp/README.md`](../mcp/README.md)).
4. **Approve it** in `config/mcp.toml`: add the name to the server's `tools`, and to each role that may see it. A server that advertises a tool not listed there is refused.
5. **Test it** like `tests/test_mcp.py`: invalid arguments, the deadline, tenant isolation, and the result's fields.

A tool that changes state must set `is_read_only=False`, and needs an approval design before it is exposed. Actions stay disabled (`Settings.external_actions_enabled` is always `False`) until that design exists.

## Tests

`tests/test_mcp.py`: argument validation, the deadline, results without the owner, and reads only in the context tenant.

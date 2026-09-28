# `mcp/` — serving tools to agents over MCP

The [Model Context Protocol](https://modelcontextprotocol.io) is the standard way a model host discovers and calls tools. Here, each tool server is a **separate process** started over stdio, and the client exposes to each agent role only the tools that role is approved for.

Why a separate process and not a plain function call: the server gets its own minimal environment (no API keys), its own tenant fixed at launch, and its own log file. That boundary is the one that later becomes a network service (Streamable HTTP) with per-request authentication, without changing the tools.

## Two independent controls

1. **Server side:** every call runs for the tenant the server was **launched** for (`--tenant`). Tool arguments cannot change it.
2. **Client side:** the role's allowlist in `config/mcp.toml` decides which tools the model even sees. The client also refuses to connect if a server advertises anything other than exactly its approved tools.

Either control alone would stop a cross-tenant read; both exist as defense in depth.

## Files

### `server.py` — exposing `BaseTool`s as MCP tools

- `build_mcp_server(name, tools, context)` creates an `MCPServer` and registers each tool; duplicate tool names raise `ValueError`.
- `register_mcp_tool(server, tool, context)` registers one tool under its `spec.name`, `spec.description`, and a `read_only_hint`. The registered function calls `tool.call_tool(context, arguments)` and returns the result dumped as JSON. An `AppError` becomes an MCP `ToolError` carrying only the safe message.
- `build_tool_signature(tool)` builds a keyword-only Python signature from the tool's argument model (with field constraints and descriptions) and its result model. `MCPServer` derives the advertised input and output JSON schemas from that signature, so the model sees exactly the Pydantic contract.
- `AnyTool` is `BaseTool[Any, Any]`, because a server holds tools of different types and each validates its own.

### `examples_server.py` — the example server process

Launched by the client as `python -m app.mcp.examples_server --project-root <root> --tenant <tenant>`. It loads settings in fixture mode, opens the database, builds the tools (`build_example_tools`: `GetExampleRecordTool` over `SqlRecordRepository`), and serves them on stdio until the client disconnects. **Stdout carries protocol messages only**: never print from a server.

### `client.py` — connecting agents to approved servers

- **`MCPCatalog`** is the validated `config/mcp.toml`: `servers` (each an `MCPServerConfig` with `module`, the exact `tools` list, `init_timeout_seconds`, and `read_timeout_seconds`) and `roles` (role → server → tools). A validator rejects a role that names an unknown server or a tool its server does not provide. `module` must match `^app(\.[a-z_]+)+$`, so only modules of this package can be launched.
- **`load_mcp_catalog(location)`** reads and validates the catalog, raising `ConfigurationError` if it is invalid.
- **`open_role_toolsets(location, catalog, *, role, scope, database_url)`** is an async context manager. For each server the role uses, it:
  1. builds the child environment with `build_server_environment`: only `PATH`, `TEMPLATE_DATABASE_URL`, `TEMPLATE_MODEL_MODE=fixture`, and the nonsecret `PLATFORM_VARIABLES`. **No API keys** and no other `TEMPLATE_` values are passed;
  2. builds an `MCPToolset` over a `StdioTransport` with `build_stdio_toolset`: it runs `sys.executable -m <module>` in `backend/`, writes stderr to `backend/data/mcp-<server>.log`, applies the catalog's timeouts, and sets `max_retries=1` with `tool_error_behavior="retry"`, so a tool error goes back to the model once before the run fails;
  3. connects and verifies the server with `_connect_verified`: it fails closed with `ToolAccessError("unexpected_tool_catalog: …")` unless the server advertises **exactly** the approved tools. An extra tool is refused as firmly as a missing one, because a server that grew a tool has changed what an agent can do;
  4. filters the toolset to the role's allowlist with `build_allowlist_filter`.

  It yields the list of toolsets, and every server stops when the context exits.

## How it connects

`foundation.py` loads the catalog. The CLI's `mcp-check` opens every role's toolsets and reports which roles it verified. An agent that uses tools receives the yielded toolsets as its `toolsets`.

## How to use

```bash
cd backend
.venv/bin/template-cli mcp-check --tenant tenant_alpha
# {"status": "ok", ..., "verified_roles": ["example_reader"], "servers": ["examples"]}
```

Giving an agent its role's tools:

```python
from pydantic_ai import Agent

from app.core.context import TenantScope
from app.foundation import Foundation
from app.mcp.client import open_role_toolsets


async def ask_with_tools(foundation: Foundation, agent: Agent[None, str], question: str) -> str:
    async with open_role_toolsets(
        foundation.location,
        foundation.mcp_catalog,
        role="example_reader",
        scope=TenantScope(tenant_id="tenant_alpha"),
        database_url=foundation.database_url,
    ) as toolsets:
        result = await agent.run(question, toolsets=toolsets)
    return result.output
```

`BaseAgent` sets `tool_calls_limit=0` for single-call agents. A tool-using agent needs its own, explicitly bounded usage limits, which is a separate design step.

## How to add a server or a role

1. **A server:** create `mcp/<name>_server.py` modelled on `examples_server.py` (parse `--project-root` and `--tenant`, open the database, build its tools, call `build_mcp_server(...).run_stdio_async()`). Add `[servers.<name>]` to `config/mcp.toml` with `module = "app.mcp.<name>_server"` and the exact `tools` list.
2. **A role:** add `[roles.<role>]` with `<server> = ["tool", ...]`, listing only the tools that role needs.
3. **Check it:** run `template-cli mcp-check --tenant <tenant>`, and add tests like `tests/test_mcp.py`.

## Tests

`tests/test_mcp.py`: advertised schemas and read-only hints, duplicate names, a real stdio server serving a database-backed tool to an agent, allowlists changing the visible tools, calls restricted to the launch tenant, fail-closed behavior on an unexpected catalog, unknown roles, catalog validation, and the child environment carrying no keys.

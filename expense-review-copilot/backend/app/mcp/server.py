"""Expose ``BaseTool`` instances as MCP tools with their Pydantic schemas.

Each tool's argument model becomes the advertised input schema, including field descriptions
and limits, and its result model becomes the output schema. Known failures reach the client as
MCP tool errors carrying only the safe application message.
"""

import inspect
from collections.abc import Sequence
from typing import Annotated, Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations
from pydantic import BaseModel

from app.core.errors import ExpenseError
from app.tools.base import BaseTool, ToolContext

# Tools are heterogeneous in their argument and result types; each validates its own.
AnyTool = BaseTool[Any, Any]


def build_mcp_server(name: str, tools: Sequence[AnyTool], context: ToolContext) -> MCPServer:
    """Create an MCP server exposing the given tools for one tenant context.

    Args:
        name: Server name reported to clients.
        tools: Tools to register; names must be unique.
        context: Tenant every call on this server runs for.

    Returns:
        A server ready for ``run_stdio_async``; nothing is started here.

    Raises:
        ValueError: Two tools share a name.
    """
    if len({tool.spec.name for tool in tools}) != len(tools):
        raise ValueError("tool names must be unique")
    server: MCPServer = MCPServer(name, log_level="WARNING", warn_on_duplicate_tools=False)
    for tool in tools:
        register_mcp_tool(server, tool, context)
    return server


def register_mcp_tool(server: MCPServer, tool: AnyTool, context: ToolContext) -> None:
    """Register one tool under its spec name, schema, and read-only hint.

    Args:
        server: Server to add the tool to.
        tool: Tool to expose.
        context: Tenant the tool's calls run for.
    """

    async def call_registered_tool(**arguments: object) -> dict[str, object]:
        try:
            result: BaseModel = await tool.call_tool(context, arguments)
        except ExpenseError as error:
            raise ToolError(str(error)) from error
        return result.model_dump(mode="json")

    # MCPServer derives schemas from the signature; build it from the argument model.
    call_registered_tool.__signature__ = build_tool_signature(tool)  # type: ignore[attr-defined]
    server.add_tool(
        call_registered_tool,
        name=tool.spec.name,
        description=tool.spec.description,
        annotations=ToolAnnotations(read_only_hint=tool.spec.is_read_only),
    )


def build_tool_signature(tool: AnyTool) -> inspect.Signature:
    """Return a keyword-only signature mirroring the tool's argument model.

    Args:
        tool: Tool whose argument fields, constraints, and descriptions are copied.

    Returns:
        A signature whose return annotation is the tool's result model.
    """
    parameters = [
        inspect.Parameter(
            name,
            inspect.Parameter.KEYWORD_ONLY,
            annotation=Annotated[field.annotation, field],
            default=inspect.Parameter.empty if field.is_required() else field.default,
        )
        for name, field in tool.arguments_type.model_fields.items()
    ]
    return inspect.Signature(parameters, return_annotation=tool.result_type)

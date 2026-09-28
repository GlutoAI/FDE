"""Connect agents to approved MCP servers, exposing only the tools their role allows.

The server independently restricts every call to its launch tenant; the client allowlist is
defense in depth, not the only control.
"""

import os
import sys
import tomllib
from collections.abc import AsyncIterator, Callable
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Any, Self

from fastmcp.client.transports import StdioTransport
from pydantic import Field, ValidationError, model_validator
from pydantic_ai import RunContext
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.tools import ToolDefinition
from pydantic_ai.toolsets import AbstractToolset

from app.core.context import TenantScope
from app.core.errors import ConfigurationError, ToolAccessError
from app.core.settings import ProjectLocation
from app.llm.contracts import Contract

ToolFilter = Callable[[RunContext[Any], ToolDefinition], bool]


class MCPServerLaunch(Contract):
    """Per-process launch facts for one server."""

    name: str = Field(min_length=1, description="Catalog name of the server")
    scope: TenantScope = Field(description="Tenant the process serves")
    environment: dict[str, str] = Field(description="Complete child process environment")


class MCPServerConfig(Contract):
    """One approved stdio server and the exact tool catalog it must advertise."""

    module: str = Field(pattern=r"^app(\.[a-z_]+)+$", description="Package module to launch")
    tools: list[str] = Field(min_length=1, description="Tools the server must advertise")
    init_timeout_seconds: float = Field(gt=0, le=60, description="Startup and handshake limit")
    read_timeout_seconds: float = Field(gt=0, le=60, description="Per-request response limit")


class MCPCatalog(Contract):
    """Approved servers and the per-role tool allowlists."""

    servers: dict[str, MCPServerConfig] = Field(description="Servers by name")
    roles: dict[str, dict[str, list[str]]] = Field(
        description="Role -> server name -> tools that role may see"
    )

    @model_validator(mode="after")
    def validate_role_tools(self) -> Self:
        """Reject roles naming unknown servers or tools a server does not provide."""
        for role, tools_by_server in self.roles.items():
            for server_name, tools in tools_by_server.items():
                server = self.servers.get(server_name)
                if server is None or not set(tools) <= set(server.tools):
                    raise ValueError(f"role {role} references unknown server or tool")
        return self


def load_mcp_catalog(location: ProjectLocation) -> MCPCatalog:
    """Read and validate ``config/mcp.toml``.

    Args:
        location: Project containing the config directory.

    Returns:
        The validated catalog; no server is started.

    Raises:
        ConfigurationError: The file is missing or invalid.
    """
    try:
        with (location.config_dir / "mcp.toml").open("rb") as stream:
            return MCPCatalog.model_validate(tomllib.load(stream))
    except (OSError, ValueError, ValidationError) as error:
        raise ConfigurationError("invalid_mcp_catalog: check config/mcp.toml") from error


@asynccontextmanager
async def open_role_toolsets(
    location: ProjectLocation,
    catalog: MCPCatalog,
    *,
    role: str,
    scope: TenantScope,
    database_url: str,
) -> AsyncIterator[list[AbstractToolset[Any]]]:
    """Start each server the role uses, verify its catalog, and yield filtered toolsets.

    Args:
        location: Project root passed to each server.
        catalog: Approved servers and role allowlists.
        role: Agent role whose tools are exposed.
        scope: Tenant each server process is launched for.
        database_url: Database the servers read; passed through the environment, not argv.

    Yields:
        One toolset per server, showing the model only the role's tools. Servers stop on exit.

    Raises:
        ConfigurationError: The role is not in the catalog.
        ToolAccessError: A server failed to start or advertised an unexpected tool catalog.
    """
    if role not in catalog.roles:
        raise ConfigurationError(f"unknown_tool_role: {role}")
    environment = build_server_environment(database_url)
    location.state_dir.mkdir(parents=True, exist_ok=True)
    async with AsyncExitStack() as stack:
        toolsets: list[AbstractToolset[Any]] = []
        for server_name, allowed_tools in catalog.roles[role].items():
            config = catalog.servers[server_name]
            launch = MCPServerLaunch(name=server_name, scope=scope, environment=environment)
            toolset = build_stdio_toolset(location, config, launch)
            await _connect_verified(stack, toolset, server_name, config)
            toolsets.append(toolset.filtered(build_allowlist_filter(frozenset(allowed_tools))))
        yield toolsets


def build_stdio_toolset(
    location: ProjectLocation, config: MCPServerConfig, launch: MCPServerLaunch
) -> MCPToolset[Any]:
    """Build an unconnected toolset that launches the server module for one tenant.

    Args:
        location: Project root passed to the server.
        config: Approved server entry.
        launch: Server name, tenant, and environment for this process.

    Returns:
        A toolset whose server exits when the toolset closes and writes its stderr to
        ``backend/data/mcp-<name>.log``; tool errors go back to the model once before the run fails.
    """
    transport = StdioTransport(
        command=sys.executable,
        args=[
            "-m",
            config.module,
            "--project-root",
            str(location.root),
            "--tenant",
            launch.scope.tenant_id,
        ],
        env=launch.environment,
        cwd=str(location.backend_root),
        keep_alive=False,
        log_file=location.state_dir / f"mcp-{launch.name}.log",
    )
    return MCPToolset(
        transport,
        init_timeout=config.init_timeout_seconds,
        read_timeout=config.read_timeout_seconds,
        max_retries=1,
        tool_error_behavior="retry",
    )


PLATFORM_VARIABLES = ("OPENSSL_armcap",)
"""Nonsecret runtime settings a child needs to start on this host; see docker/Dockerfile.api."""


def build_server_environment(database_url: str) -> dict[str, str]:
    """Return the minimal child environment: no API keys and no inherited CASHFLOW_ values.

    Args:
        database_url: Database the server must use.

    Returns:
        PATH, the database URL, fixture model mode, and any set ``PLATFORM_VARIABLES``.
    """
    platform = {name: os.environ[name] for name in PLATFORM_VARIABLES if name in os.environ}
    return platform | {
        "PATH": os.environ.get("PATH", ""),
        "CASHFLOW_DATABASE_URL": database_url,
        "CASHFLOW_MODEL_MODE": "fixture",
    }


def build_allowlist_filter(allowed_tools: frozenset[str]) -> ToolFilter:
    """Return a toolset filter admitting only the named tools.

    Args:
        allowed_tools: Tool names the role may see.

    Returns:
        A predicate for ``AbstractToolset.filtered``.
    """

    def is_allowed(context: RunContext[Any], tool: ToolDefinition) -> bool:
        return tool.name in allowed_tools

    return is_allowed


async def _connect_verified(
    stack: AsyncExitStack, toolset: MCPToolset[Any], server_name: str, config: MCPServerConfig
) -> None:
    """Start the server and fail closed unless it advertises exactly the approved tools."""
    try:
        await stack.enter_async_context(toolset)
        advertised = sorted(tool.name for tool in await toolset.list_tools())
    except (OSError, RuntimeError, TimeoutError) as error:
        raise ToolAccessError(f"mcp_unavailable: {server_name} did not start") from error
    if advertised != sorted(config.tools):
        raise ToolAccessError(f"unexpected_tool_catalog: {server_name}")

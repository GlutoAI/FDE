"""Run the example MCP server over stdio for one tenant.

Launched by the MCP client as ``python -m app.mcp.examples_server``. The tenant is fixed by the
launching host for the life of the process; authenticated per-request identity replaces this
when servers move to Streamable HTTP. Stdout carries protocol messages only.
"""

import argparse
import asyncio
from collections.abc import Sequence
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.context import TenantScope
from app.core.settings import ProjectLocation, load_settings
from app.db.engine import build_database_url, open_database
from app.db.records import ExampleRecord
from app.db.repository import SqlRecordRepository
from app.db.tables import example_records
from app.mcp.server import AnyTool, build_mcp_server
from app.tools.base import ToolContext
from app.tools.examples import GetExampleRecordTool

SERVER_NAME = "agentic-project-template-examples"


def build_example_tools(engine: AsyncEngine) -> list[AnyTool]:
    """Create the example tools over SQL repositories.

    Args:
        engine: Open database engine.

    Returns:
        Every example tool; the client decides which ones an agent may see.
    """
    return [GetExampleRecordTool(SqlRecordRepository(engine, example_records, ExampleRecord))]


async def serve_example_tools(location: ProjectLocation, scope: TenantScope) -> None:
    """Open the database and serve example tools on stdio until the client disconnects.

    Args:
        location: Project whose settings select the database.
        scope: Tenant every call on this server runs for.

    Raises:
        ConfigurationError: Settings are invalid.
        StorageError: The database cannot be opened.
    """
    settings = load_settings(location, execution_mode="fixture")
    configured_url = settings.database_url.get_secret_value() if settings.database_url else None
    async with open_database(build_database_url(location.state_dir, configured_url)) as engine:
        server = build_mcp_server(
            SERVER_NAME, build_example_tools(engine), ToolContext(scope=scope)
        )
        await server.run_stdio_async()


def run_examples_server(arguments: Sequence[str] | None = None) -> None:
    """Parse the launch arguments and serve until stdin closes.

    Args:
        arguments: Command-line arguments; defaults to ``sys.argv[1:]``.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--tenant", required=True)
    parsed = parser.parse_args(arguments)
    location = ProjectLocation(root=parsed.project_root.resolve())
    asyncio.run(serve_example_tools(location, TenantScope(tenant_id=parsed.tenant)))


if __name__ == "__main__":
    run_examples_server()

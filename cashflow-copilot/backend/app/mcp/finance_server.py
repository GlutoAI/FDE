"""Run the finance MCP server over stdio for one tenant.

Launched by the MCP client as ``python -m app.mcp.finance_server``. The tenant is
fixed by the launching host for the life of the process; authenticated per-request identity
replaces this in the Streamable HTTP phase. Stdout carries protocol messages only.
"""

import argparse
import asyncio
from collections.abc import Sequence
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.context import TenantScope
from app.core.settings import ProjectLocation, load_settings
from app.db.engine import build_database_url, open_database
from app.db.records import CustomerRecord, InvoiceRecord
from app.db.repository import SqlRecordRepository
from app.db.tables import customers, invoices
from app.mcp.server import AnyTool, build_mcp_server
from app.tools.base import ToolContext
from app.tools.finance import GetCustomerTool, ListCustomerInvoicesTool

SERVER_NAME = "cashflow-finance"


def build_finance_tools(engine: AsyncEngine) -> list[AnyTool]:
    """Create the finance tools over SQL repositories.

    Args:
        engine: Open database engine.

    Returns:
        Every finance tool; the client decides which ones an agent may see.
    """
    return [
        GetCustomerTool(SqlRecordRepository(engine, customers, CustomerRecord)),
        ListCustomerInvoicesTool(SqlRecordRepository(engine, invoices, InvoiceRecord)),
    ]


async def serve_finance_tools(location: ProjectLocation, scope: TenantScope) -> None:
    """Open the database and serve finance tools on stdio until the client disconnects.

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
            SERVER_NAME, build_finance_tools(engine), ToolContext(scope=scope)
        )
        await server.run_stdio_async()


def run_finance_server(arguments: Sequence[str] | None = None) -> None:
    """Parse the launch arguments and serve until stdin closes.

    Args:
        arguments: Command-line arguments; defaults to ``sys.argv[1:]``.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--tenant", required=True)
    parsed = parser.parse_args(arguments)
    location = ProjectLocation(root=parsed.project_root.resolve())
    asyncio.run(serve_finance_tools(location, TenantScope(tenant_id=parsed.tenant)))


if __name__ == "__main__":
    run_finance_server()

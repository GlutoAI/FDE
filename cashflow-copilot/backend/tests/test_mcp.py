import asyncio
from pathlib import Path
from typing import override

import pytest
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from app.core.context import TenantScope
from app.core.errors import ConfigurationError, RecordNotFoundError, ToolAccessError
from app.core.settings import ProjectLocation
from app.db.csv_import import import_structured_data, load_csv_records
from app.db.engine import build_database_url, open_database
from app.db.records import CustomerRecord, InvoiceRecord
from app.db.repository import InMemoryRecordRepository
from app.mcp.client import build_server_environment, load_mcp_catalog, open_role_toolsets
from app.mcp.server import build_mcp_server
from app.tools.base import BaseTool, ToolContext, ToolSpec
from app.tools.finance import (
    CustomerLookup,
    CustomerSummary,
    GetCustomerTool,
    ListCustomerInvoicesTool,
)

DATA_ROOT = Path(__file__).resolve().parents[2] / "data"
AURORA_CONTEXT = ToolContext(scope=TenantScope(tenant_id="tenant_aurora"))


def build_customer_repository() -> InMemoryRecordRepository[CustomerRecord]:
    repository = InMemoryRecordRepository[CustomerRecord]()
    records = load_csv_records(DATA_ROOT / "structured/customers.csv", CustomerRecord)
    asyncio.run(repository.save_records(records))
    return repository


class SlowTool(BaseTool[CustomerLookup, CustomerSummary]):
    def __init__(self) -> None:
        spec = ToolSpec(
            name="slow", version=1, description="Sleeps.", is_read_only=True, timeout_seconds=0.01
        )
        super().__init__(spec, CustomerLookup, CustomerSummary)

    @override
    async def _run_tool(self, context: ToolContext, arguments: CustomerLookup) -> CustomerSummary:
        await asyncio.sleep(1)
        raise AssertionError("deadline was not enforced")


def test_tool_rejects_arguments_that_violate_its_contract() -> None:
    tool = GetCustomerTool(build_customer_repository())
    with pytest.raises(ToolAccessError, match="invalid_arguments: get_customer"):
        asyncio.run(tool.call_tool(AURORA_CONTEXT, {"customer_id": "not a valid id!"}))


def test_tool_enforces_its_deadline() -> None:
    with pytest.raises(ToolAccessError, match="timeout: slow"):
        asyncio.run(SlowTool().call_tool(AURORA_CONTEXT, {"customer_id": "CUS-A-001"}))


def test_get_customer_reads_only_the_context_tenant() -> None:
    tool = GetCustomerTool(build_customer_repository())
    summary = asyncio.run(tool.call_tool(AURORA_CONTEXT, {"customer_id": "CUS-A-001"}))
    assert summary.display_name == "Harbor & Pine Retail"
    assert "email" not in summary.model_dump()
    with pytest.raises(RecordNotFoundError):
        asyncio.run(tool.call_tool(AURORA_CONTEXT, {"customer_id": "CUS-C-001"}))


def test_list_customer_invoices_orders_newest_due_first_and_limits() -> None:
    repository = InMemoryRecordRepository[InvoiceRecord]()
    asyncio.run(
        repository.save_records(
            load_csv_records(DATA_ROOT / "structured/invoices.csv", InvoiceRecord)
        )
    )
    tool = ListCustomerInvoicesTool(repository)
    arguments = {"customer_id": "CUS-A-001", "limit": 2}
    result = asyncio.run(tool.call_tool(AURORA_CONTEXT, arguments))
    due_dates = [invoice.due_date for invoice in result.invoices]
    assert len(due_dates) == 2 and due_dates == sorted(due_dates, reverse=True)


def test_mcp_server_advertises_argument_schema_and_read_only_hint() -> None:
    server = build_mcp_server(
        "test", [GetCustomerTool(build_customer_repository())], AURORA_CONTEXT
    )
    [tool] = asyncio.run(server.list_tools())
    customer_id = tool.input_schema["properties"]["customer_id"]
    assert tool.name == "get_customer"
    assert customer_id["description"].startswith("Customer ID")
    assert "pattern" in customer_id
    assert tool.annotations is not None and tool.annotations.read_only_hint is True
    assert tool.output_schema is not None and "display_name" in tool.output_schema["properties"]


def test_build_mcp_server_rejects_duplicate_tool_names() -> None:
    repository = build_customer_repository()
    with pytest.raises(ValueError):
        build_mcp_server(
            "test", [GetCustomerTool(repository), GetCustomerTool(repository)], AURORA_CONTEXT
        )


@pytest.fixture
def seeded_project(project_location: ProjectLocation) -> tuple[ProjectLocation, str]:
    database_url = build_database_url(project_location.state_dir, None)

    async def seed() -> None:
        async with open_database(database_url) as engine:
            await import_structured_data(DATA_ROOT / "structured", engine)

    asyncio.run(seed())
    return project_location, database_url


def build_scripted_model(customer_id: str) -> tuple[FunctionModel, list[list[str]]]:
    tools_seen: list[list[str]] = []

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        tools_seen.append(sorted(tool.name for tool in info.function_tools))
        if len(messages) == 1:
            return ModelResponse(parts=[ToolCallPart("get_customer", {"customer_id": customer_id})])
        return ModelResponse(parts=[TextPart(str(messages[-1].parts[-1].content))])  # type: ignore[union-attr]

    return FunctionModel(respond), tools_seen


def run_role_agent(
    seeded_project: tuple[ProjectLocation, str], *, role: str, tenant_id: str, customer_id: str
) -> tuple[str, list[list[str]]]:
    location, database_url = seeded_project
    model, tools_seen = build_scripted_model(customer_id)

    async def run_agent() -> str:
        catalog = load_mcp_catalog(location)
        scope = TenantScope(tenant_id=tenant_id)
        async with open_role_toolsets(
            location, catalog, role=role, scope=scope, database_url=database_url
        ) as toolsets:
            result = await Agent(model, toolsets=toolsets).run("Look up the customer.")
            return result.output

    return asyncio.run(run_agent()), tools_seen


def test_stdio_server_serves_database_backed_tool_to_an_agent(
    seeded_project: tuple[ProjectLocation, str],
) -> None:
    output, tools_seen = run_role_agent(
        seeded_project, role="customer_lookup", tenant_id="tenant_aurora", customer_id="CUS-A-001"
    )
    assert "Harbor & Pine Retail" in output
    assert tools_seen[0] == ["get_customer"]


def test_stdio_role_allowlist_changes_visible_tools(
    seeded_project: tuple[ProjectLocation, str],
) -> None:
    _, tools_seen = run_role_agent(
        seeded_project,
        role="receivables_reader",
        tenant_id="tenant_aurora",
        customer_id="CUS-A-001",
    )
    assert tools_seen[0] == ["get_customer", "list_customer_invoices"]


def test_stdio_server_restricts_calls_to_its_launch_tenant(
    seeded_project: tuple[ProjectLocation, str],
) -> None:
    output, _ = run_role_agent(
        seeded_project, role="customer_lookup", tenant_id="tenant_copper", customer_id="CUS-A-001"
    )
    assert "record_not_found" in output
    assert "Harbor" not in output


def test_open_role_toolsets_fails_closed_on_unexpected_catalog(
    seeded_project: tuple[ProjectLocation, str],
) -> None:
    location, _ = seeded_project
    path = location.config_dir / "mcp.toml"
    text = path.read_text().replace(
        'tools = ["get_customer", "list_customer_invoices"]', 'tools = ["get_customer"]'
    )
    path.write_text(text.split("[roles.receivables_reader]")[0])
    with pytest.raises(ToolAccessError, match="unexpected_tool_catalog: finance"):
        run_role_agent(
            seeded_project,
            role="customer_lookup",
            tenant_id="tenant_aurora",
            customer_id="CUS-A-001",
        )


def test_open_role_toolsets_rejects_unknown_role(
    seeded_project: tuple[ProjectLocation, str],
) -> None:
    with pytest.raises(ConfigurationError, match="unknown_tool_role"):
        run_role_agent(
            seeded_project, role="admin", tenant_id="tenant_aurora", customer_id="CUS-A-001"
        )


def test_load_mcp_catalog_rejects_role_with_unknown_tool(project_location: ProjectLocation) -> None:
    path = project_location.config_dir / "mcp.toml"
    path.write_text(
        path.read_text().replace('finance = ["get_customer"]', 'finance = ["send_email"]')
    )
    with pytest.raises(ConfigurationError, match="invalid_mcp_catalog"):
        load_mcp_catalog(project_location)


def test_server_environment_passes_platform_settings_but_no_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENSSL_armcap", "0")
    monkeypatch.setenv("CASHFLOW_LLM_API_KEY", "child-test-secret")
    monkeypatch.setenv("UNRELATED_SETTING", "value")
    environment = build_server_environment("sqlite+aiosqlite:///db")
    assert set(environment) == {
        "PATH",
        "CASHFLOW_DATABASE_URL",
        "CASHFLOW_MODEL_MODE",
        "OPENSSL_armcap",
    }
    assert "child-test-secret" not in environment.values()

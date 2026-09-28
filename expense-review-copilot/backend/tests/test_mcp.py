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
from app.db.csv_import import import_structured_data
from app.db.engine import build_database_url, open_database
from app.db.records import ExpenseRecord
from app.db.repository import InMemoryRecordRepository
from app.mcp.client import build_server_environment, load_mcp_catalog, open_role_toolsets
from app.mcp.server import build_mcp_server
from app.tools.base import BaseTool, ToolContext, ToolSpec
from app.tools.expenses import ExpenseLookup, ExpenseSummary, GetExpenseTool
from tests.synthetic import ALPHA, SYNTHETIC_EXPENSES, write_expense_import

ALPHA_CONTEXT = ToolContext(scope=ALPHA)


def build_expense_repository() -> InMemoryRecordRepository[ExpenseRecord]:
    repository = InMemoryRecordRepository[ExpenseRecord]()
    asyncio.run(repository.save_records(SYNTHETIC_EXPENSES))
    return repository


class SlowTool(BaseTool[ExpenseLookup, ExpenseSummary]):
    def __init__(self) -> None:
        spec = ToolSpec(
            name="slow", version=1, description="Sleeps.", is_read_only=True, timeout_seconds=0.01
        )
        super().__init__(spec, ExpenseLookup, ExpenseSummary)

    @override
    async def _run_tool(self, context: ToolContext, arguments: ExpenseLookup) -> ExpenseSummary:
        await asyncio.sleep(1)
        raise AssertionError("deadline was not enforced")


def test_tool_rejects_arguments_that_violate_its_contract() -> None:
    tool = GetExpenseTool(build_expense_repository())
    with pytest.raises(ToolAccessError, match="invalid_arguments: get_expense"):
        asyncio.run(tool.call_tool(ALPHA_CONTEXT, {"expense_id": "not a valid id!"}))


def test_tool_enforces_its_deadline() -> None:
    with pytest.raises(ToolAccessError, match="timeout: slow"):
        asyncio.run(SlowTool().call_tool(ALPHA_CONTEXT, {"expense_id": "EXP-1001"}))


def test_get_expense_reports_receipt_status_without_the_submitter() -> None:
    tool = GetExpenseTool(build_expense_repository())
    with_receipt = asyncio.run(tool.call_tool(ALPHA_CONTEXT, {"expense_id": "EXP-1001"}))
    missing = asyncio.run(tool.call_tool(ALPHA_CONTEXT, {"expense_id": "EXP-1002"}))
    assert (with_receipt.merchant, with_receipt.has_receipt) == ("Harbor Cafe", True)
    assert (missing.expense_date, missing.has_receipt) == ("2026-09-02", False)
    assert "submitted_by" not in missing.model_dump()


def test_get_expense_reads_only_the_context_tenant() -> None:
    tool = GetExpenseTool(build_expense_repository())
    summary = asyncio.run(tool.call_tool(ALPHA_CONTEXT, {"expense_id": "EXP-1001"}))
    assert summary.merchant != "Summit Supplies"
    with pytest.raises(RecordNotFoundError):
        asyncio.run(tool.call_tool(ALPHA_CONTEXT, {"expense_id": "EXP-9999"}))


def test_mcp_server_advertises_argument_schema_and_read_only_hint() -> None:
    server = build_mcp_server("test", [GetExpenseTool(build_expense_repository())], ALPHA_CONTEXT)
    [tool] = asyncio.run(server.list_tools())
    expense_id = tool.input_schema["properties"]["expense_id"]
    assert tool.name == "get_expense"
    assert expense_id["description"].startswith("Expense ID")
    assert "pattern" in expense_id
    assert tool.annotations is not None and tool.annotations.read_only_hint is True
    assert tool.output_schema is not None and "has_receipt" in tool.output_schema["properties"]


def test_build_mcp_server_rejects_duplicate_tool_names() -> None:
    repository = build_expense_repository()
    with pytest.raises(ValueError):
        build_mcp_server(
            "test", [GetExpenseTool(repository), GetExpenseTool(repository)], ALPHA_CONTEXT
        )


@pytest.fixture
def seeded_project(
    project_location: ProjectLocation, tmp_path: Path
) -> tuple[ProjectLocation, str]:
    database_url = build_database_url(project_location.state_dir, None)
    directory = write_expense_import(tmp_path / "import", has_preferences=False)

    async def seed() -> None:
        async with open_database(database_url) as engine:
            await import_structured_data(directory, engine)

    asyncio.run(seed())
    return project_location, database_url


def build_scripted_model(expense_id: str) -> tuple[FunctionModel, list[list[str]]]:
    tools_seen: list[list[str]] = []

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        tools_seen.append(sorted(tool.name for tool in info.function_tools))
        if len(messages) == 1 and info.function_tools:
            return ModelResponse(parts=[ToolCallPart("get_expense", {"expense_id": expense_id})])
        return ModelResponse(parts=[TextPart(str(messages[-1].parts[-1].content))])  # type: ignore[union-attr]

    return FunctionModel(respond), tools_seen


def run_role_agent(
    seeded_project: tuple[ProjectLocation, str],
    *,
    role: str = "expense_reader",
    tenant_id: str = "tenant_alpha",
    expense_id: str = "EXP-1001",
) -> tuple[str, list[list[str]]]:
    location, database_url = seeded_project
    model, tools_seen = build_scripted_model(expense_id)

    async def run_agent() -> str:
        catalog = load_mcp_catalog(location)
        scope = TenantScope(tenant_id=tenant_id)
        async with open_role_toolsets(
            location, catalog, role=role, scope=scope, database_url=database_url
        ) as toolsets:
            result = await Agent(model, toolsets=toolsets).run("Look up the expense.")
            return result.output

    return asyncio.run(run_agent()), tools_seen


def test_stdio_server_serves_database_backed_tool_to_an_agent(
    seeded_project: tuple[ProjectLocation, str],
) -> None:
    output, tools_seen = run_role_agent(seeded_project)
    assert "Harbor Cafe" in output
    assert tools_seen[0] == ["get_expense"]


def test_stdio_role_allowlist_changes_visible_tools(
    seeded_project: tuple[ProjectLocation, str],
) -> None:
    location, _ = seeded_project
    path = location.config_dir / "mcp.toml"
    path.write_text(path.read_text() + "\n[roles.no_tools]\nexpenses = []\n")
    _, tools_seen = run_role_agent(seeded_project, role="no_tools")
    assert tools_seen[0] == []


def test_stdio_server_restricts_calls_to_its_launch_tenant(
    seeded_project: tuple[ProjectLocation, str],
) -> None:
    output, _ = run_role_agent(seeded_project, tenant_id="tenant_beta", expense_id="EXP-1002")
    assert "record_not_found" in output
    assert "Harbor" not in output


def test_open_role_toolsets_fails_closed_on_unexpected_catalog(
    seeded_project: tuple[ProjectLocation, str],
) -> None:
    location, _ = seeded_project
    path = location.config_dir / "mcp.toml"
    text = path.read_text().replace(
        'tools = ["get_expense"]', 'tools = ["get_expense", "approve_expense"]'
    )
    path.write_text(text)
    with pytest.raises(ToolAccessError, match="unexpected_tool_catalog: expenses"):
        run_role_agent(seeded_project)


def test_open_role_toolsets_rejects_unknown_role(
    seeded_project: tuple[ProjectLocation, str],
) -> None:
    with pytest.raises(ConfigurationError, match="unknown_tool_role"):
        run_role_agent(seeded_project, role="admin")


def test_load_mcp_catalog_rejects_role_with_unknown_tool(project_location: ProjectLocation) -> None:
    path = project_location.config_dir / "mcp.toml"
    path.write_text(
        path.read_text().replace('expenses = ["get_expense"]', 'expenses = ["send_email"]')
    )
    with pytest.raises(ConfigurationError, match="invalid_mcp_catalog"):
        load_mcp_catalog(project_location)


def test_server_environment_passes_platform_settings_but_no_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENSSL_armcap", "0")
    monkeypatch.setenv("EXPENSE_OPENAI_API_KEY", "child-test-secret")
    monkeypatch.setenv("UNRELATED_SETTING", "value")
    environment = build_server_environment("sqlite+aiosqlite:///db")
    assert set(environment) == {
        "PATH",
        "EXPENSE_DATABASE_URL",
        "EXPENSE_MODEL_MODE",
        "OPENSSL_armcap",
    }
    assert "child-test-secret" not in environment.values()

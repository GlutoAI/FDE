"""Verify tools, the MCP server builder, and real stdio servers behind role allowlists.

The stdio tests start ``app.mcp.examples_server`` as a subprocess; a scripted
``FunctionModel`` stands in for the LLM, so no model is called.
"""

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
from app.db.records import ExampleRecord
from app.db.repository import InMemoryRecordRepository
from app.mcp.client import build_server_environment, load_mcp_catalog, open_role_toolsets
from app.mcp.server import build_mcp_server
from app.tools.base import BaseTool, ToolContext, ToolSpec
from app.tools.examples import ExampleRecordLookup, ExampleRecordSummary, GetExampleRecordTool
from tests.synthetic import ALPHA, SYNTHETIC_RECORDS, write_record_import

ALPHA_CONTEXT = ToolContext(scope=ALPHA)


def build_record_repository() -> InMemoryRecordRepository[ExampleRecord]:
    """Return an in-memory repository holding every synthetic record."""
    repository = InMemoryRecordRepository[ExampleRecord]()
    asyncio.run(repository.save_records(SYNTHETIC_RECORDS))
    return repository


class SlowTool(BaseTool[ExampleRecordLookup, ExampleRecordSummary]):
    """A tool that outlives its 10 ms deadline, to prove ``call_tool`` enforces it."""

    def __init__(self) -> None:
        """Declare the tool with a deadline far shorter than its sleep."""
        spec = ToolSpec(
            name="slow", version=1, description="Sleeps.", is_read_only=True, timeout_seconds=0.01
        )
        super().__init__(spec, ExampleRecordLookup, ExampleRecordSummary)

    @override
    async def _run_tool(
        self, context: ToolContext, arguments: ExampleRecordLookup
    ) -> ExampleRecordSummary:
        await asyncio.sleep(1)
        raise AssertionError("deadline was not enforced")


def test_tool_rejects_arguments_that_violate_its_contract() -> None:
    tool = GetExampleRecordTool(build_record_repository())
    with pytest.raises(ToolAccessError, match="invalid_arguments: get_example_record"):
        asyncio.run(tool.call_tool(ALPHA_CONTEXT, {"record_id": "not a valid id!"}))


def test_tool_enforces_its_deadline() -> None:
    with pytest.raises(ToolAccessError, match="timeout: slow"):
        asyncio.run(SlowTool().call_tool(ALPHA_CONTEXT, {"record_id": "REC-1001"}))


def test_get_example_record_reports_open_status_without_the_owner() -> None:
    tool = GetExampleRecordTool(build_record_repository())
    closed = asyncio.run(tool.call_tool(ALPHA_CONTEXT, {"record_id": "REC-1001"}))
    still_open = asyncio.run(tool.call_tool(ALPHA_CONTEXT, {"record_id": "REC-1002"}))
    assert (closed.name, closed.is_open) == ("Harbor Cafe", False)
    assert (still_open.opened_on, still_open.is_open) == ("2026-09-02", True)
    assert "owner_id" not in still_open.model_dump()


def test_get_example_record_reads_only_the_context_tenant() -> None:
    tool = GetExampleRecordTool(build_record_repository())
    summary = asyncio.run(tool.call_tool(ALPHA_CONTEXT, {"record_id": "REC-1001"}))
    assert summary.name != "Summit Supplies"
    with pytest.raises(RecordNotFoundError):
        asyncio.run(tool.call_tool(ALPHA_CONTEXT, {"record_id": "REC-9999"}))


def test_mcp_server_advertises_argument_schema_and_read_only_hint() -> None:
    server = build_mcp_server(
        "test", [GetExampleRecordTool(build_record_repository())], ALPHA_CONTEXT
    )
    [tool] = asyncio.run(server.list_tools())
    record_id = tool.input_schema["properties"]["record_id"]
    assert tool.name == "get_example_record"
    assert record_id["description"].startswith("Record ID")
    assert "pattern" in record_id
    assert tool.annotations is not None and tool.annotations.read_only_hint is True
    assert tool.output_schema is not None and "is_open" in tool.output_schema["properties"]


def test_build_mcp_server_rejects_duplicate_tool_names() -> None:
    repository = build_record_repository()
    with pytest.raises(ValueError):
        build_mcp_server(
            "test",
            [GetExampleRecordTool(repository), GetExampleRecordTool(repository)],
            ALPHA_CONTEXT,
        )


@pytest.fixture
def seeded_project(
    project_location: ProjectLocation, tmp_path: Path
) -> tuple[ProjectLocation, str]:
    database_url = build_database_url(project_location.state_dir, None)
    directory = write_record_import(tmp_path / "import", has_preferences=False)

    async def seed() -> None:
        async with open_database(database_url) as engine:
            await import_structured_data(directory, engine)

    asyncio.run(seed())
    return project_location, database_url


def build_scripted_model(record_id: str) -> tuple[FunctionModel, list[list[str]]]:
    """Return a model that calls the example tool once, then echoes the tool's result.

    The second value records the tool names the model was shown on each turn.
    """
    tools_seen: list[list[str]] = []

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        tools_seen.append(sorted(tool.name for tool in info.function_tools))
        if len(messages) == 1 and info.function_tools:
            return ModelResponse(
                parts=[ToolCallPart("get_example_record", {"record_id": record_id})]
            )
        return ModelResponse(parts=[TextPart(str(messages[-1].parts[-1].content))])  # type: ignore[union-attr]

    return FunctionModel(respond), tools_seen


def run_role_agent(
    seeded_project: tuple[ProjectLocation, str],
    *,
    role: str = "example_reader",
    tenant_id: str = "tenant_alpha",
    record_id: str = "REC-1001",
) -> tuple[str, list[list[str]]]:
    """Run the scripted agent through a real stdio server; return its output and tools seen."""
    location, database_url = seeded_project
    model, tools_seen = build_scripted_model(record_id)

    async def run_agent() -> str:
        catalog = load_mcp_catalog(location)
        scope = TenantScope(tenant_id=tenant_id)
        async with open_role_toolsets(
            location, catalog, role=role, scope=scope, database_url=database_url
        ) as toolsets:
            result = await Agent(model, toolsets=toolsets).run("Look up the record.")
            return result.output

    return asyncio.run(run_agent()), tools_seen


def test_stdio_server_serves_database_backed_tool_to_an_agent(
    seeded_project: tuple[ProjectLocation, str],
) -> None:
    output, tools_seen = run_role_agent(seeded_project)
    assert "Harbor Cafe" in output
    assert tools_seen[0] == ["get_example_record"]


def test_stdio_role_allowlist_changes_visible_tools(
    seeded_project: tuple[ProjectLocation, str],
) -> None:
    location, _ = seeded_project
    path = location.config_dir / "mcp.toml"
    path.write_text(path.read_text() + "\n[roles.no_tools]\nexamples = []\n")
    _, tools_seen = run_role_agent(seeded_project, role="no_tools")
    assert tools_seen[0] == []


def test_stdio_server_restricts_calls_to_its_launch_tenant(
    seeded_project: tuple[ProjectLocation, str],
) -> None:
    output, _ = run_role_agent(seeded_project, tenant_id="tenant_beta", record_id="REC-1002")
    assert "record_not_found" in output
    assert "Harbor" not in output


def test_open_role_toolsets_fails_closed_on_unexpected_catalog(
    seeded_project: tuple[ProjectLocation, str],
) -> None:
    location, _ = seeded_project
    path = location.config_dir / "mcp.toml"
    text = path.read_text().replace(
        'tools = ["get_example_record"]', 'tools = ["get_example_record", "approve_record"]'
    )
    path.write_text(text)
    with pytest.raises(ToolAccessError, match="unexpected_tool_catalog: examples"):
        run_role_agent(seeded_project)


def test_open_role_toolsets_rejects_unknown_role(
    seeded_project: tuple[ProjectLocation, str],
) -> None:
    with pytest.raises(ConfigurationError, match="unknown_tool_role"):
        run_role_agent(seeded_project, role="admin")


def test_load_mcp_catalog_rejects_role_with_unknown_tool(project_location: ProjectLocation) -> None:
    path = project_location.config_dir / "mcp.toml"
    path.write_text(
        path.read_text().replace('examples = ["get_example_record"]', 'examples = ["send_email"]')
    )
    with pytest.raises(ConfigurationError, match="invalid_mcp_catalog"):
        load_mcp_catalog(project_location)


def test_server_environment_passes_platform_settings_but_no_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENSSL_armcap", "0")
    monkeypatch.setenv("TEMPLATE_OPENAI_API_KEY", "child-test-secret")
    monkeypatch.setenv("UNRELATED_SETTING", "value")
    environment = build_server_environment("sqlite+aiosqlite:///db")
    assert set(environment) == {
        "PATH",
        "TEMPLATE_DATABASE_URL",
        "TEMPLATE_MODEL_MODE",
        "OPENSSL_armcap",
    }
    assert "child-test-secret" not in environment.values()

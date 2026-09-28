import asyncio
import json
import shutil
import sys
from pathlib import Path

import pytest
from pydantic import SecretStr

from app.cli import run_cli
from app.core.context import TenantScope
from app.core.errors import ConfigurationError
from app.core.settings import ProjectLocation, load_settings
from app.foundation import import_seed_data, open_foundation

DATA_ROOT = Path(__file__).resolve().parents[2] / "data"
AURORA_DOCUMENT_IDS = {
    entry["document_id"]
    for entry in json.loads((DATA_ROOT / "documents/index.json").read_text())
    if entry["tenant_id"] == "tenant_aurora"
}


@pytest.fixture
def data_project(project_location: ProjectLocation) -> ProjectLocation:
    shutil.copytree(DATA_ROOT, project_location.root / "data")
    return project_location


def run_command(
    location: ProjectLocation,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    *arguments: str,
) -> tuple[int, dict[str, object]]:
    monkeypatch.setattr(sys, "argv", ["cashflow", *arguments, "--project-root", str(location.root)])
    exit_code = run_cli()
    return exit_code, json.loads(capsys.readouterr().out)


def test_open_foundation_composes_empty_database_offline(data_project: ProjectLocation) -> None:
    settings = load_settings(data_project)

    async def scenario() -> None:
        async with open_foundation(data_project, settings) as foundation:
            assert foundation.embedder.profile.provider == "fixture"
            aurora = TenantScope(tenant_id="tenant_aurora")
            assert await foundation.customers.list_records(aurora, limit=10) == []
            reports = await import_seed_data(foundation, data_project.root / "data")
            assert [r.table for r in reports] == ["customers", "invoices", "memory_preferences"]
            assert len(await foundation.preferences.list_active_preferences(aurora)) == 2
            assert "database_url" not in repr(foundation)

    asyncio.run(scenario())
    assert (data_project.state_dir / "app.db").exists()


def test_open_foundation_live_embeddings_require_the_openai_key(
    data_project: ProjectLocation,
) -> None:
    settings = load_settings(data_project).model_copy(
        update={"model_mode": "live", "anthropic_api_key": SecretStr("anthropic-test-secret")}
    )

    async def open_live() -> None:
        async with open_foundation(data_project, settings):
            pass

    with pytest.raises(ConfigurationError, match="CASHFLOW_LLM_API_KEY"):
        asyncio.run(open_live())


def test_cli_runs_offline_pipeline_from_import_to_search_and_mcp(
    data_project: ProjectLocation,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, imported = run_command(data_project, monkeypatch, capsys, "data-import")
    assert code == 0
    assert [item["rows_read"] for item in imported["imports"]] == [15, 53, 3]  # type: ignore[union-attr, index]

    code, indexed = run_command(data_project, monkeypatch, capsys, "index-documents")
    assert (code, indexed["documents"], indexed["mode"]) == (0, 27, "fixture")

    code, found = run_command(
        data_project,
        monkeypatch,
        capsys,
        "search",
        "--tenant",
        "tenant_aurora",
        "--query",
        "contract amendment",
    )
    document_ids = {item["document_id"] for item in found["results"]}  # type: ignore[union-attr, index]
    assert code == 0 and document_ids and document_ids <= AURORA_DOCUMENT_IDS

    code, checked = run_command(
        data_project, monkeypatch, capsys, "mcp-check", "--tenant", "tenant_aurora"
    )
    assert (code, checked["verified_roles"]) == (0, ["customer_lookup", "receivables_reader"])


@pytest.mark.parametrize(
    ("arguments", "reason"),
    [
        (["search", "--query", "cash"], "search requires --tenant"),
        (["search", "--tenant", "tenant_aurora"], "search requires --query"),
        (["data-import", "--live"], "--live belongs to"),
        (["mcp-check"], "mcp-check requires --tenant"),
        (["mcp-check", "--tenant", "Not-A-Tenant"], "invalid tenant_id"),
        (["search", "--tenant", "tenant_aurora", "--query", "x" * 2001], "invalid text"),
    ],
)
def test_cli_rejects_options_outside_their_command(
    arguments: list[str],
    reason: str,
    data_project: ProjectLocation,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, output = run_command(data_project, monkeypatch, capsys, *arguments)
    assert code == 1 and reason in str(output["reason"])


def test_cli_config_check_hides_a_configured_database_url(
    data_project: ProjectLocation,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("CASHFLOW_DATABASE_URL", "postgresql+asyncpg://app:db-secret@localhost/x")
    code, output = run_command(data_project, monkeypatch, capsys, "config-check")
    assert (code, output["database"]) == (0, "configured_url")
    assert output["embedding_index"] == "fixture:hashing-embedder-v1:256"
    assert "db-secret" not in json.dumps(output)

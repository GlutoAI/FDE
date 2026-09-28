"""Run the composed foundation and the CLI end to end on synthetic data, fully offline."""

import asyncio
import json
import sys
from pathlib import Path

import pytest
from pydantic import SecretStr

from app.cli import run_cli
from app.core.errors import ConfigurationError
from app.core.settings import ProjectLocation, load_settings
from app.foundation import import_seed_data, open_foundation
from tests.synthetic import ALPHA, write_document_import, write_record_import


@pytest.fixture
def data_project(project_location: ProjectLocation) -> ProjectLocation:
    raw = project_location.data_root / "raw"
    write_record_import(raw / "records/2026-09-27")
    write_document_import(raw / "documents/2026-09-27")
    return project_location


def import_directory(location: ProjectLocation, kind: str) -> str:
    """Return the dated raw directory ``data_project`` wrote for ``records`` or ``documents``."""
    return str(location.data_root / "raw" / kind / "2026-09-27")


def run_command(
    location: ProjectLocation,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    *arguments: str,
) -> tuple[int, dict[str, object]]:
    """Invoke the CLI in-process and return its exit code and parsed JSON output."""
    monkeypatch.setattr(
        sys, "argv", ["template-cli", *arguments, "--project-root", str(location.root)]
    )
    exit_code = run_cli()
    return exit_code, json.loads(capsys.readouterr().out)


def test_open_foundation_composes_empty_database_offline(data_project: ProjectLocation) -> None:
    settings = load_settings(data_project)

    async def scenario() -> None:
        async with open_foundation(data_project, settings) as foundation:
            assert foundation.embedder.profile.provider == "fixture"
            assert await foundation.example_records.list_records(ALPHA, limit=10) == []
            directory = Path(import_directory(data_project, "records"))
            reports = await import_seed_data(foundation, directory)
            assert [r.table for r in reports] == ["example_records", "memory_preferences"]
            assert len(await foundation.preferences.list_active_preferences(ALPHA)) == 2
            assert (
                await foundation.example_records.get_record(ALPHA, "REC-1002")
            ).closed_on is None
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

    with pytest.raises(ConfigurationError, match="TEMPLATE_OPENAI_API_KEY"):
        asyncio.run(open_live())


def test_cli_runs_offline_pipeline_from_import_to_search_and_mcp(
    data_project: ProjectLocation,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    records_directory = import_directory(data_project, "records")
    code, imported = run_command(
        data_project, monkeypatch, capsys, "data-import", "--directory", records_directory
    )
    assert code == 0
    assert [item["rows_read"] for item in imported["imports"]] == [4, 3]  # type: ignore[union-attr, index]

    documents_directory = import_directory(data_project, "documents")
    code, indexed = run_command(
        data_project, monkeypatch, capsys, "index-documents", "--directory", documents_directory
    )
    assert (code, indexed["documents"], indexed["mode"]) == (0, 2, "fixture")

    code, found = run_command(
        data_project,
        monkeypatch,
        capsys,
        "search",
        "--tenant",
        "tenant_alpha",
        "--query",
        "what needs a supporting document",
    )
    document_ids = {item["document_id"] for item in found["results"]}  # type: ignore[union-attr, index]
    assert (code, document_ids) == (0, {"policy-alpha"})

    code, checked = run_command(
        data_project, monkeypatch, capsys, "mcp-check", "--tenant", "tenant_alpha"
    )
    assert (code, checked["verified_roles"]) == (0, ["example_reader"])


@pytest.mark.parametrize(
    ("arguments", "reason"),
    [
        (["search", "--query", "cash"], "search requires --tenant"),
        (["search", "--tenant", "tenant_alpha"], "search requires --query"),
        (["data-import", "--live"], "--live belongs to"),
        (["data-import"], "--directory is required by"),
        (["search", "--tenant", "tenant_alpha", "--query", "x", "--directory", "."], "--directory"),
        (["mcp-check"], "mcp-check requires --tenant"),
        (["mcp-check", "--tenant", "Not-A-Tenant"], "invalid tenant_id"),
        (["search", "--tenant", "tenant_alpha", "--query", "x" * 2001], "invalid text"),
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
    monkeypatch.setenv("TEMPLATE_DATABASE_URL", "postgresql+asyncpg://app:db-secret@localhost/x")
    code, output = run_command(data_project, monkeypatch, capsys, "config-check")
    assert (code, output["database"]) == (0, "configured_url")
    assert output["embedding_index"] == "fixture:hashing-embedder-v1:256"
    assert "db-secret" not in json.dumps(output)

"""Prove live requests require an explicit flag and failure output is safe."""

import json
import sys

import pytest

from app.cli import run_cli
from app.core.settings import ProjectLocation


@pytest.mark.parametrize("command", ["config-check", "smoke"])
def test_cli_runs_offline_without_credentials(
    command: str,
    project_location: ProjectLocation,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sys, "argv", ["expense", command, "--project-root", str(project_location.root)]
    )
    assert run_cli() == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "ok"
    assert result["mode"] == "fixture"


def test_cli_live_without_key_fails_instead_of_using_fixture(
    project_location: ProjectLocation,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sys, "argv", ["expense", "smoke", "--live", "--project-root", str(project_location.root)]
    )
    assert run_cli() == 1
    assert json.loads(capsys.readouterr().out)["status"] == "failed"


def test_cli_config_check_reports_key_presence_per_vendor(
    project_location: ProjectLocation,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (project_location.root / ".env").write_text("EXPENSE_ANTHROPIC_API_KEY=test-secret\n")
    monkeypatch.setattr(
        sys, "argv", ["expense", "config-check", "--project-root", str(project_location.root)]
    )
    assert run_cli() == 0
    output = capsys.readouterr().out
    assert json.loads(output)["keys_present"] == {"openai": False, "anthropic": True}
    assert "test-secret" not in output


@pytest.mark.parametrize(
    "arguments", [["smoke", "--provider", "anthropic"], ["config-check", "--provider", "openai"]]
)
def test_cli_rejects_provider_without_live_smoke(
    arguments: list[str],
    project_location: ProjectLocation,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sys, "argv", ["expense", *arguments, "--project-root", str(project_location.root)]
    )
    assert run_cli() == 1
    assert "invalid_option" in json.loads(capsys.readouterr().out)["reason"]


def test_cli_live_anthropic_without_its_key_fails(
    project_location: ProjectLocation,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (project_location.root / ".env").write_text("EXPENSE_OPENAI_API_KEY=openai-test-secret\n")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "expense",
            "smoke",
            "--live",
            "--provider",
            "anthropic",
            "--project-root",
            str(project_location.root),
        ],
    )
    assert run_cli() == 1
    output = capsys.readouterr().out
    assert json.loads(output)["reason"] == "missing_credentials: set EXPENSE_ANTHROPIC_API_KEY"
    assert "openai-test-secret" not in output


@pytest.mark.parametrize("key_entry", ["", "EXPENSE_OPENAI_API_KEY=test-secret\n"])
def test_cli_live_config_does_not_make_ordinary_smoke_live(
    project_location: ProjectLocation,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    key_entry: str,
) -> None:
    (project_location.root / ".env").write_text("EXPENSE_MODEL_MODE=live\n" + key_entry)
    monkeypatch.setattr(
        sys, "argv", ["expense", "smoke", "--project-root", str(project_location.root)]
    )
    assert run_cli() == 0
    assert json.loads(capsys.readouterr().out)["mode"] == "fixture"

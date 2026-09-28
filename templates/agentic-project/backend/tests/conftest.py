"""Hermetic test configuration; real network access and developer keys are excluded."""

import os
import shutil
import socket
from pathlib import Path

import pytest

from app.core.settings import ProjectLocation


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in os.environ:
        if name.startswith(("TEMPLATE_", "OPENAI_", "ANTHROPIC_")):
            monkeypatch.delenv(name)

    def reject_network(*arguments: object, **keywords: object) -> None:
        raise AssertionError("Default tests must never reach the network")

    monkeypatch.setattr(socket.socket, "connect", reject_network)


@pytest.fixture
def project_location(tmp_path: Path) -> ProjectLocation:
    location = ProjectLocation(root=tmp_path)
    shutil.copytree(Path(__file__).resolve().parents[1] / "config", location.config_dir)
    return location

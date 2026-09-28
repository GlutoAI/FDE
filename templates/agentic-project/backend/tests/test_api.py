"""Exercise the HTTP routes through FastAPI's test client against a temporary project."""

import json

import pytest
from fastapi.testclient import TestClient

from app.core.settings import ProjectLocation
from app.main import create_app
from app.routers import health


def test_health_reports_connected_database_in_template_shape(
    project_location: ProjectLocation,
) -> None:
    with TestClient(create_app(project_location)) as client:
        response = client.get("/health")
    assert (response.status_code, response.json()) == (200, {"status": "ok", "db": "connected"})
    assert (project_location.state_dir / "app.db").exists()


def test_health_returns_503_with_safe_code_when_database_fails(
    project_location: ProjectLocation, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fail_check(engine: object) -> bool:
        return False

    monkeypatch.setattr(health, "is_database_reachable", fail_check)
    with TestClient(create_app(project_location)) as client:
        response = client.get("/health")
    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "db": "disconnected",
        "detail": "database_unavailable",
    }


def test_connection_diagnostic_stays_on_fixture_even_in_live_mode(
    project_location: ProjectLocation,
) -> None:
    project_location.env_file.write_text(
        "TEMPLATE_MODEL_MODE=live\nTEMPLATE_OPENAI_API_KEY=api-test-secret\n"
    )
    with TestClient(create_app(project_location)) as client:
        response = client.post("/diagnostics/connection")
    body = response.json()
    assert response.status_code == 200
    assert (body["provider"], body["output"]["marker"]) == ("fixture", "CONNECTION_OK")
    assert "api-test-secret" not in json.dumps(body)


def test_cors_allows_the_local_frontend_origin(project_location: ProjectLocation) -> None:
    with TestClient(create_app(project_location)) as client:
        response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"

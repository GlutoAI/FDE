"""Prove the YAML-selected model reaches the real Pydantic AI request boundary.

The vendor SDK clients are real; only their HTTP transport is mocked, so each test sees exactly
what would have been sent over the network.
"""

import asyncio
import json

import httpx
import pytest
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from pydantic import SecretStr

from app.agents.connection.models import ConnectionInput, ConnectionOutput
from app.bootstrap import create_connection_agent
from app.core.errors import ConfigurationError
from app.core.settings import ProjectLocation, Settings, load_settings
from app.llm.contracts import AgentResult, LiveProviderName, PromptReference
from app.llm.prompts import load_prompt

VALID_OUTPUT = '{"status":"ok","marker":"CONNECTION_OK"}'
YAML_MODEL = "gpt-5.5"


def build_openai_response(model_id: str) -> dict[str, object]:
    """Return a completed Responses API body that names ``model_id`` as the served model."""
    return {
        "id": "resp_yaml",
        "object": "response",
        "created_at": 1,
        "status": "completed",
        "model": model_id,
        "output": [
            {
                "type": "message",
                "id": "msg_yaml",
                "status": "completed",
                "role": "assistant",
                "content": [{"type": "output_text", "text": VALID_OUTPUT, "annotations": []}],
            }
        ],
    }


def build_anthropic_response(model_id: str) -> dict[str, object]:
    """Return a completed Messages API body that names ``model_id`` as the served model."""
    return {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": model_id,
        "content": [{"type": "text", "text": VALID_OUTPUT}],
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {"input_tokens": 10, "output_tokens": 12},
    }


def patch_openai_client(monkeypatch: pytest.MonkeyPatch, bodies: list[dict[str, object]]) -> None:
    """Make bootstrap's OpenAI client answer from a mock transport that records request bodies."""

    def respond(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        bodies.append(body)
        return httpx.Response(200, json=build_openai_response(body["model"]))

    def create_client(
        *, api_key: str, base_url: str, max_retries: int, timeout: float
    ) -> AsyncOpenAI:
        transport = httpx.MockTransport(respond)
        return AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            max_retries=max_retries,
            timeout=timeout,
            http_client=httpx.AsyncClient(transport=transport),
        )

    monkeypatch.setattr("app.bootstrap.AsyncOpenAI", create_client)


def patch_anthropic_client(monkeypatch: pytest.MonkeyPatch, requests: list[httpx.Request]) -> None:
    """Make bootstrap's Anthropic client answer from a mock transport that records requests.

    The factory also asserts bootstrap pins the official base URL and disables SDK retries.
    """

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        model_id = json.loads(request.content)["model"]
        return httpx.Response(200, json=build_anthropic_response(model_id))

    def create_client(
        *, api_key: str, base_url: str, max_retries: int, timeout: float
    ) -> AsyncAnthropic:
        assert (base_url, max_retries) == ("https://api.anthropic.com", 0)
        return AsyncAnthropic(
            api_key=api_key,
            base_url=base_url,
            max_retries=max_retries,
            timeout=timeout,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond)),
        )

    monkeypatch.setattr("app.bootstrap.AsyncAnthropic", create_client)


def use_yaml_model(monkeypatch: pytest.MonkeyPatch, model_id: str) -> None:
    """Make bootstrap load the connection prompt with ``model`` set, as an agent YAML may."""
    prompt = load_prompt(PromptReference(agent="connection", version=1))
    prompt = prompt.model_copy(
        update={"template": prompt.template.model_copy(update={"model": model_id})}
    )
    monkeypatch.setattr("app.bootstrap.load_prompt", lambda reference: prompt)


def run_probe(
    location: ProjectLocation, settings: Settings, *, vendor: LiveProviderName | None = None
) -> AgentResult[ConnectionOutput]:
    """Compose the connection agent through bootstrap and run it once."""

    async def probe() -> AgentResult[ConnectionOutput]:
        async with create_connection_agent(location, settings, vendor=vendor) as agent:
            return await agent.run_agent(ConnectionInput())

    return asyncio.run(probe())


def test_bootstrap_sends_the_yaml_model_in_live_mode(
    project_location: ProjectLocation, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_yaml_model(monkeypatch, YAML_MODEL)
    bodies: list[dict[str, object]] = []
    patch_openai_client(monkeypatch, bodies)
    settings = load_settings(project_location).model_copy(
        update={"model_mode": "live", "openai_api_key": SecretStr("test-secret")}
    )

    result = run_probe(project_location, settings)

    assert [body["model"] for body in bodies] == [YAML_MODEL]
    assert result.model_id == YAML_MODEL


def test_bootstrap_yaml_model_does_not_escape_fixture_mode(
    project_location: ProjectLocation, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_yaml_model(monkeypatch, YAML_MODEL)
    bodies: list[dict[str, object]] = []
    patch_openai_client(monkeypatch, bodies)
    settings = load_settings(project_location).model_copy(
        update={"openai_api_key": SecretStr("test-secret")}
    )

    result = run_probe(project_location, settings)

    assert bodies == []
    assert result.model_id == "connection-fixture-v1"


def test_bootstrap_routes_anthropic_vendor_to_anthropic_client(
    project_location: ProjectLocation, monkeypatch: pytest.MonkeyPatch
) -> None:
    requests: list[httpx.Request] = []
    patch_anthropic_client(monkeypatch, requests)
    settings = load_settings(project_location).model_copy(
        update={"model_mode": "live", "anthropic_api_key": SecretStr("test-secret")}
    )

    result = run_probe(project_location, settings, vendor="anthropic")

    assert (result.provider, result.model_id) == ("anthropic", "claude-opus-5-5")
    assert [request.url.host for request in requests] == ["api.anthropic.com"]


def test_bootstrap_names_missing_vendor_key_without_values(
    project_location: ProjectLocation,
) -> None:
    settings = load_settings(project_location).model_copy(
        update={"model_mode": "live", "openai_api_key": SecretStr("openai-test-secret")}
    )

    with pytest.raises(ConfigurationError) as failure:
        run_probe(project_location, settings, vendor="anthropic")

    assert "TEMPLATE_ANTHROPIC_API_KEY" in str(failure.value)
    assert "openai-test-secret" not in str(failure.value)

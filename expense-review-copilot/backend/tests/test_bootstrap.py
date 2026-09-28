"""Prove the YAML-selected model reaches the real Pydantic AI request boundary."""

import asyncio
import json

import httpx
import pytest
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from pydantic import SecretStr

from app.agents.connection.models import ConnectionInput
from app.bootstrap import create_connection_agent
from app.core.errors import ConfigurationError
from app.core.settings import ProjectLocation, load_settings
from app.llm.contracts import PromptReference
from app.llm.prompts import load_prompt


@pytest.mark.parametrize("mode", ["fixture", "live"])
def test_bootstrap_resolves_yaml_model_without_escaping_fixture_mode(
    project_location: ProjectLocation,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    prompt = load_prompt(PromptReference(agent="connection", version=1))
    prompt = prompt.model_copy(
        update={"template": prompt.template.model_copy(update={"model": "gpt-5.5"})}
    )
    monkeypatch.setattr("app.bootstrap.load_prompt", lambda reference: prompt)
    requests: list[dict[str, object]] = []

    def respond(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append(body)
        return httpx.Response(
            200,
            json={
                "id": "resp_yaml",
                "object": "response",
                "created_at": 1,
                "status": "completed",
                "model": body["model"],
                "output": [
                    {
                        "type": "message",
                        "id": "msg_yaml",
                        "status": "completed",
                        "role": "assistant",
                        "content": [
                            {
                                "type": "output_text",
                                "text": '{"status":"ok","marker":"CONNECTION_OK"}',
                                "annotations": [],
                            }
                        ],
                    }
                ],
            },
        )

    def create_client(
        *, api_key: str, base_url: str, max_retries: int, timeout: float
    ) -> AsyncOpenAI:
        return AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            max_retries=max_retries,
            timeout=timeout,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond)),
        )

    monkeypatch.setattr("app.bootstrap.AsyncOpenAI", create_client)
    settings = load_settings(project_location).model_copy(
        update={"model_mode": mode, "openai_api_key": SecretStr("test-secret")}
    )

    async def run_probe() -> str:
        async with create_connection_agent(project_location, settings) as agent:
            return (await agent.run_agent(ConnectionInput())).model_id

    model_id = asyncio.run(run_probe())
    if mode == "live":
        assert len(requests) == 1
        assert requests[0]["model"] == "gpt-5.5"
        assert model_id == "gpt-5.5"
    else:
        assert not requests
        assert model_id == "connection-fixture-v1"


def test_bootstrap_routes_anthropic_vendor_to_anthropic_client(
    project_location: ProjectLocation,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "model": json.loads(request.content)["model"],
                "content": [{"type": "text", "text": '{"status":"ok","marker":"CONNECTION_OK"}'}],
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 10, "output_tokens": 12},
            },
        )

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
    settings = load_settings(project_location).model_copy(
        update={"model_mode": "live", "anthropic_api_key": SecretStr("test-secret")}
    )

    async def run_probe() -> tuple[str, str]:
        async with create_connection_agent(project_location, settings, vendor="anthropic") as agent:
            result = await agent.run_agent(ConnectionInput())
            return result.provider, result.model_id

    assert asyncio.run(run_probe()) == ("anthropic", "claude-opus-5-5")
    assert len(requests) == 1
    assert requests[0].url.host == "api.anthropic.com"


def test_bootstrap_names_missing_vendor_key_without_values(
    project_location: ProjectLocation,
) -> None:
    settings = load_settings(project_location).model_copy(
        update={"model_mode": "live", "openai_api_key": SecretStr("openai-test-secret")}
    )

    async def open_agent() -> None:
        async with create_connection_agent(project_location, settings, vendor="anthropic"):
            pass

    with pytest.raises(ConfigurationError) as failure:
        asyncio.run(open_agent())
    assert "EXPENSE_ANTHROPIC_API_KEY" in str(failure.value)
    assert "openai-test-secret" not in str(failure.value)

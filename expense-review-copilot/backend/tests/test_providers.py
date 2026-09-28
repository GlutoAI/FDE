"""Exercise Pydantic AI through fixture, OpenAI, and Anthropic adapters without a network."""

import asyncio
import json
from collections.abc import Callable

import httpx
import pytest
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from pydantic_ai import NativeOutput, ToolOutput
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.openai import OpenAIProvider

from app.agents.connection.models import ConnectionInput, ConnectionOutput
from app.bootstrap import build_connection_agent
from app.core.errors import AgentOutputError, ConfigurationError, ProviderError
from app.llm.contracts import AgentResult, ModelProfile, PromptReference
from app.llm.prompts import load_prompt
from app.llm.provider import ModelProvider
from app.llm.providers.anthropic import AnthropicModelProvider
from app.llm.providers.fixture import FixtureModelProvider
from app.llm.providers.openai import OpenAIModelProvider

VALID_OUTPUT = '{"status":"ok","marker":"CONNECTION_OK"}'
MODEL_IDS = {
    "fixture": "gpt-5.4-mini-2026-03-17",
    "openai": "gpt-5.4-mini-2026-03-17",
    "anthropic": "claude-opus-5-5",
}


def build_response() -> dict[str, object]:
    return {
        "id": "resp_test",
        "object": "response",
        "created_at": 1,
        "status": "completed",
        "model": "gpt-5.4-mini-2026-03-17",
        "output": [
            {
                "type": "message",
                "id": "msg_test",
                "status": "completed",
                "role": "assistant",
                "content": [{"type": "output_text", "text": VALID_OUTPUT, "annotations": []}],
            }
        ],
        "usage": {"input_tokens": 10, "output_tokens": 12, "total_tokens": 22},
    }


def build_anthropic_response() -> dict[str, object]:
    return {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": "claude-opus-5-5",
        "content": [{"type": "text", "text": VALID_OUTPUT}],
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {"input_tokens": 10, "output_tokens": 12},
    }


def build_anthropic_model(transport: httpx.MockTransport, model_id: str) -> AnthropicModel:
    client = AsyncAnthropic(
        api_key="test-secret", max_retries=0, http_client=httpx.AsyncClient(transport=transport)
    )
    return AnthropicModel(model_id, provider=AnthropicProvider(anthropic_client=client))


async def run_provider_probe(
    transport: httpx.MockTransport,
    *,
    kind: str = "openai",
) -> AgentResult[ConnectionOutput]:
    profile = ModelProfile(
        provider=kind, model_id=MODEL_IDS[kind], timeout_seconds=2, max_output_tokens=128
    )
    prompt = load_prompt(PromptReference(agent="connection", version=1))
    async with AsyncOpenAI(
        api_key="test-secret", max_retries=0, http_client=httpx.AsyncClient(transport=transport)
    ) as client:
        provider: ModelProvider
        if kind == "fixture":
            provider = FixtureModelProvider(
                TestModel(
                    custom_output_text=VALID_OUTPUT,
                    profile={"supports_json_schema_output": True},
                )
            )
        elif kind == "anthropic":
            provider = AnthropicModelProvider(build_anthropic_model(transport, profile.model_id))
        else:
            provider = OpenAIModelProvider(
                OpenAIResponsesModel(
                    profile.model_id, provider=OpenAIProvider(openai_client=client)
                )
            )
        agent = build_connection_agent(provider, prompt, profile)
        return await agent.run_agent(ConnectionInput())


def respond_with(kind: str) -> Callable[[httpx.Request], httpx.Response]:
    body = build_anthropic_response() if kind == "anthropic" else build_response()
    return lambda request: httpx.Response(200, json=body)


@pytest.mark.parametrize("kind", ["fixture", "openai", "anthropic"])
def test_provider_contract_returns_typed_agent_output(kind: str) -> None:
    transport = httpx.MockTransport(respond_with(kind))
    result = asyncio.run(run_provider_probe(transport, kind=kind))
    assert isinstance(result.output, ConnectionOutput)
    assert result.output.marker == "CONNECTION_OK"
    assert result.status == "ok"
    assert result.provider == kind


@pytest.mark.parametrize(
    ("status", "code", "expected"),
    [
        (401, "invalid_api_key", "authentication"),
        (403, "forbidden", "permission"),
        (404, "model_not_found", "model_unavailable"),
        (429, "insufficient_quota", "quota"),
        (429, "rate_limit_exceeded", "rate_limit"),
        (400, "invalid_request", "invalid_request"),
        (500, "server_error", "provider_error"),
    ],
)
def test_provider_failures_are_safe_and_not_retried(status: int, code: str, expected: str) -> None:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(status, json={"error": {"code": code, "message": "test-secret"}})

    with pytest.raises(ProviderError) as failure:
        asyncio.run(run_provider_probe(httpx.MockTransport(respond)))
    assert str(failure.value).startswith(expected)
    assert "test-secret" not in str(failure.value)
    assert len(requests) == 1


@pytest.mark.parametrize(
    ("status", "error_type", "expected"),
    [
        (401, "authentication_error", "authentication"),
        (403, "permission_error", "permission"),
        (404, "not_found_error", "model_unavailable"),
        (429, "rate_limit_error", "rate_limit"),
        (400, "invalid_request_error", "invalid_request"),
        (529, "overloaded_error", "provider_error"),
    ],
)
def test_anthropic_failures_are_safe_and_not_retried(
    status: int, error_type: str, expected: str
) -> None:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        body = {"type": "error", "error": {"type": error_type, "message": "test-secret"}}
        return httpx.Response(status, json=body)

    with pytest.raises(ProviderError) as failure:
        asyncio.run(run_provider_probe(httpx.MockTransport(respond), kind="anthropic"))
    assert str(failure.value).startswith(expected)
    assert "test-secret" not in str(failure.value)
    assert len(requests) == 1


@pytest.mark.parametrize("kind", ["openai", "anthropic"])
@pytest.mark.parametrize(
    ("failure_type", "expected"), [(httpx.ConnectError, "network"), (httpx.ReadTimeout, "timeout")]
)
def test_provider_classifies_transport_failures(
    kind: str, failure_type: type[httpx.TransportError], expected: str
) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        raise failure_type("test-secret", request=request)

    with pytest.raises(ProviderError) as failure:
        asyncio.run(run_provider_probe(httpx.MockTransport(respond), kind=kind))
    assert str(failure.value).startswith(expected)
    assert "test-secret" not in str(failure.value)


def test_provider_sends_native_schema_and_validated_input_without_tools() -> None:
    bodies: list[dict[str, object]] = []

    def respond(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json=build_response())

    result = asyncio.run(run_provider_probe(httpx.MockTransport(respond)))
    assert len(bodies) == 1
    assert bodies[0]["max_output_tokens"] == 128
    assert bodies[0]["store"] is False
    assert not bodies[0].get("tools")
    assert bodies[0]["text"]["format"]["type"] == "json_schema"
    schema = bodies[0]["text"]["format"]["schema"]
    assert set(schema["required"]) == {"status", "marker"}
    assert schema["additionalProperties"] is False
    assert "expected_marker" in json.dumps(bodies[0]["input"])
    assert result.input_tokens == 10


def test_anthropic_sends_native_schema_and_validated_input_without_tools() -> None:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=build_anthropic_response())

    result = asyncio.run(run_provider_probe(httpx.MockTransport(respond), kind="anthropic"))
    body = json.loads(requests[0].content)
    assert len(requests) == 1
    assert requests[0].url.path == "/v1/messages"
    assert body["model"] == "claude-opus-5-5"
    assert body["max_tokens"] == 128
    assert not body.get("tools")
    assert body["output_config"]["format"]["type"] == "json_schema"
    assert set(body["output_config"]["format"]["schema"]["required"]) == {"status", "marker"}
    assert "expected_marker" in json.dumps(body["messages"])
    assert result.model_id == "claude-opus-5-5"
    assert result.input_tokens == 10


def test_anthropic_uses_tool_output_for_model_without_native_schema() -> None:
    transport = httpx.MockTransport(respond_with("anthropic"))
    native = AnthropicModelProvider(build_anthropic_model(transport, "claude-opus-5-5"))
    legacy = AnthropicModelProvider(build_anthropic_model(transport, "claude-3-5-haiku-20241022"))
    assert isinstance(native.build_output_spec(ConnectionOutput), NativeOutput)
    assert isinstance(legacy.build_output_spec(ConnectionOutput), ToolOutput)


def test_anthropic_rejects_unmapped_reasoning_effort() -> None:
    provider = AnthropicModelProvider(
        build_anthropic_model(httpx.MockTransport(respond_with("anthropic")), "claude-opus-5-5")
    )
    profile = ModelProfile(
        provider="anthropic",
        model_id="claude-opus-5-5",
        timeout_seconds=2,
        max_output_tokens=128,
        reasoning_effort="low",
    )
    with pytest.raises(ConfigurationError, match="reasoning_effort"):
        provider.build_model_settings(profile)


@pytest.mark.parametrize("status", ["incomplete", "failed"])
def test_provider_rejects_incomplete_responses(status: str) -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=build_response() | {"status": status})
    )
    with pytest.raises((AgentOutputError, ProviderError)):
        asyncio.run(run_provider_probe(transport))


def test_anthropic_rejects_truncated_response() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200, json=build_anthropic_response() | {"stop_reason": "max_tokens"}
        )
    )
    with pytest.raises((AgentOutputError, ProviderError)):
        asyncio.run(run_provider_probe(transport, kind="anthropic"))


@pytest.mark.parametrize("overrides", [{"output": None}, {"output": []}, {"model": None}])
def test_provider_rejects_malformed_fields(overrides: dict[str, object]) -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=build_response() | overrides)
    )
    with pytest.raises((AgentOutputError, ProviderError)):
        asyncio.run(run_provider_probe(transport))


def test_provider_keeps_absent_usage_unknown() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=build_response() | {"usage": None})
    )
    result = asyncio.run(run_provider_probe(transport))
    assert result.input_tokens is None
    assert result.output_tokens is None


@pytest.mark.parametrize("kind", ["openai", "anthropic"])
def test_provider_does_not_repair_invalid_output(kind: str) -> None:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        content = build_anthropic_response() if kind == "anthropic" else build_response()
        if kind == "anthropic":
            content["content"] = [{"type": "text", "text": '{"marker":"bad"}'}]
        else:
            content["output"][0]["content"][0]["text"] = '{"marker":"bad"}'
        return httpx.Response(200, json=content)

    with pytest.raises(AgentOutputError):
        asyncio.run(run_provider_probe(httpx.MockTransport(respond), kind=kind))
    assert len(requests) == 1

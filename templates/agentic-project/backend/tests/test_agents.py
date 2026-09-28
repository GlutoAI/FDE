"""Verify runtime input validation and Pydantic AI native output validation."""

import asyncio

import pytest
from pydantic import ValidationError
from pydantic_ai.models.test import TestModel

from app.agents.base import BaseAgent
from app.agents.connection.models import ConnectionInput, ConnectionOutput
from app.bootstrap import build_connection_agent
from app.core.errors import AgentInputError, AgentOutputError, ConfigurationError
from app.llm.contracts import ModelProfile, PromptReference
from app.llm.prompts import load_prompt
from app.llm.provider import ModelProvider
from app.llm.providers.fixture import FixtureModelProvider


def test_abcs_cannot_be_instantiated() -> None:
    with pytest.raises(TypeError):
        ModelProvider()  # type: ignore[abstract]
    with pytest.raises(TypeError):
        BaseAgent(None, None, None, input_type=ConnectionInput)  # type: ignore[abstract, arg-type]


def test_connection_agent_returns_typed_output_and_provenance() -> None:
    prompt = load_prompt(PromptReference(agent="connection", version=1))
    model = TestModel(
        custom_output_text='{"status":"ok","marker":"CONNECTION_OK"}',
        profile={"supports_json_schema_output": True},
    )
    profile = ModelProfile(
        provider="fixture", model_id="fixture", timeout_seconds=2, max_output_tokens=128
    )
    agent = build_connection_agent(FixtureModelProvider(model), prompt, profile)
    result = asyncio.run(agent.run_agent(ConnectionInput()))
    assert isinstance(result.output, ConnectionOutput)
    assert result.output.marker == "CONNECTION_OK"
    assert result.prompt_sha256 == prompt.sha256
    assert result.prompt_version == 1
    assert result.input_tokens is None
    assert model.last_model_request_parameters.output_mode == "native"
    assert model.last_model_request_parameters.function_tools == []


@pytest.mark.parametrize(
    "output",
    [
        '{"status":"ok"}',
        '{"status":"bad","marker":"CONNECTION_OK"}',
        '{"status":"ok","marker":"wrong"}',
        '{"status":"ok","marker":42}',
        '{"status":"ok","marker":"CONNECTION_OK","extra":"unexpected"}',
        "not-json-secret-like-text",
    ],
)
def test_connection_agent_rejects_invalid_structured_output(output: str) -> None:
    prompt = load_prompt(PromptReference(agent="connection", version=1))
    model = TestModel(custom_output_text=output, profile={"supports_json_schema_output": True})
    profile = ModelProfile(
        provider="fixture", model_id="fixture", timeout_seconds=2, max_output_tokens=128
    )
    agent = build_connection_agent(FixtureModelProvider(model), prompt, profile)
    with pytest.raises(AgentOutputError) as failure:
        asyncio.run(agent.run_agent(ConnectionInput()))
    assert output not in str(failure.value)


def test_connection_agent_revalidates_constructed_input_before_model_call() -> None:
    prompt = load_prompt(PromptReference(agent="connection", version=1))
    model = TestModel(profile={"supports_json_schema_output": True})
    profile = ModelProfile(
        provider="fixture", model_id="fixture", timeout_seconds=2, max_output_tokens=128
    )
    agent = build_connection_agent(FixtureModelProvider(model), prompt, profile)
    with pytest.raises(AgentInputError):
        asyncio.run(agent.run_agent(ConnectionInput.model_construct(expected_marker="invalid")))
    assert model.last_model_request_parameters is None


def test_prompt_reference_prevents_path_traversal() -> None:
    with pytest.raises(ValidationError):
        PromptReference(agent="../../.env", version=1)


def test_load_prompt_reports_missing_version() -> None:
    with pytest.raises(ConfigurationError, match="invalid_prompt"):
        load_prompt(PromptReference(agent="connection", version=999))


@pytest.mark.parametrize(
    "content",
    [
        "!!python/object/apply:os.system ['echo unexpected']",
        "agent: wrong\nversion: 1\nsystem: text\nuser: text\n",
        "agent: connection\nversion: 1\nsystem: text\nuser: text\nunexpected: 1\n",
        "[invalid yaml",
    ],
)
def test_load_prompt_rejects_unsafe_or_invalid_yaml(
    content: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from unittest.mock import Mock

    resource = Mock()
    resource.joinpath.return_value.read_bytes.return_value = content.encode()
    monkeypatch.setattr("app.llm.prompts.files", lambda package: resource)
    with pytest.raises(ConfigurationError):
        load_prompt(PromptReference(agent="connection", version=1))

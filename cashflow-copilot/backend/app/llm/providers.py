"""Fixture, OpenAI, and Anthropic implementations of the application-owned provider ABC."""

from typing import override

import anthropic
import openai
from pydantic_ai import NativeOutput, ToolOutput
from pydantic_ai.models import Model
from pydantic_ai.models.anthropic import AnthropicModel, AnthropicModelSettings
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings
from pydantic_ai.models.test import TestModel
from pydantic_ai.settings import ModelSettings

from app.core.errors import ConfigurationError
from app.llm.contracts import ModelProfile
from app.llm.provider import ModelProvider, OutputT


class FixtureModelProvider(ModelProvider):
    """An offline provider backed by Pydantic AI's schema-aware test model."""

    def __init__(self, model: TestModel) -> None:
        """Store an initialized test model without I/O.

        Args:
            model: Scripted Pydantic AI test model; all requests remain offline.
        """
        self._model = model

    @override
    def get_model(self) -> Model:
        return self._model

    @override
    def build_model_settings(self, profile: ModelProfile) -> ModelSettings:
        return ModelSettings(max_tokens=profile.max_output_tokens, timeout=profile.timeout_seconds)

    @override
    def build_output_spec(
        self, output_type: type[OutputT]
    ) -> NativeOutput[OutputT] | ToolOutput[OutputT]:
        return NativeOutput(output_type)

    @override
    def classify_sdk_error(self, error: BaseException | None) -> str | None:
        return None


class OpenAIModelProvider(ModelProvider):
    """A provider backed by Pydantic AI's OpenAI Responses adapter."""

    def __init__(self, model: OpenAIResponsesModel) -> None:
        """Store the centrally configured model without I/O.

        Args:
            model: Responses model using the externally owned async SDK client.
        """
        self._model = model

    @override
    def get_model(self) -> Model:
        return self._model

    @override
    def build_model_settings(self, profile: ModelProfile) -> ModelSettings:
        settings = OpenAIResponsesModelSettings(
            max_tokens=profile.max_output_tokens,
            timeout=profile.timeout_seconds,
            openai_store=False,
        )
        if profile.reasoning_effort is not None:
            settings["openai_reasoning_effort"] = profile.reasoning_effort
        return settings

    @override
    def build_output_spec(
        self, output_type: type[OutputT]
    ) -> NativeOutput[OutputT] | ToolOutput[OutputT]:
        return NativeOutput(output_type)

    @override
    def classify_sdk_error(self, error: BaseException | None) -> str | None:
        if isinstance(error, openai.APITimeoutError):
            return "timeout"
        if isinstance(error, openai.APIConnectionError):
            return "network"
        if isinstance(error, openai.APIResponseValidationError):
            return "invalid_response"
        return None


class AnthropicModelProvider(ModelProvider):
    """A provider backed by Pydantic AI's Anthropic Messages adapter."""

    def __init__(self, model: AnthropicModel) -> None:
        """Store the centrally configured model without I/O.

        Args:
            model: Messages model using the externally owned async SDK client.
        """
        self._model = model

    @override
    def get_model(self) -> Model:
        return self._model

    @override
    def build_model_settings(self, profile: ModelProfile) -> ModelSettings:
        """Return shared limits; reasoning effort is not translated for Anthropic yet.

        Raises:
            ConfigurationError: The profile sets reasoning_effort, which has no mapping here.
        """
        if profile.reasoning_effort is not None:
            raise ConfigurationError(
                "unsupported_model_configuration: reasoning_effort is not mapped for anthropic"
            )
        return AnthropicModelSettings(
            max_tokens=profile.max_output_tokens, timeout=profile.timeout_seconds
        )

    @override
    def build_output_spec(
        self, output_type: type[OutputT]
    ) -> NativeOutput[OutputT] | ToolOutput[OutputT]:
        if self._model.profile.get("supports_json_schema_output", False):
            return NativeOutput(output_type)
        return ToolOutput(output_type)

    @override
    def classify_sdk_error(self, error: BaseException | None) -> str | None:
        if isinstance(error, anthropic.APITimeoutError):
            return "timeout"
        if isinstance(error, anthropic.APIConnectionError):
            return "network"
        if isinstance(error, anthropic.APIResponseValidationError):
            return "invalid_response"
        return None

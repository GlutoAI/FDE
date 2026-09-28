"""Anthropic through Pydantic AI's Messages adapter, on an SDK client owned by bootstrap."""

from typing import override

import anthropic
from pydantic_ai import NativeOutput, ToolOutput
from pydantic_ai.models import Model
from pydantic_ai.models.anthropic import AnthropicModel, AnthropicModelSettings
from pydantic_ai.settings import ModelSettings

from app.core.errors import ConfigurationError
from app.llm.contracts import ModelProfile
from app.llm.provider import ModelProvider, OutputT


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
        # Only newer Claude models accept a JSON schema; older ones return output via a tool.
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

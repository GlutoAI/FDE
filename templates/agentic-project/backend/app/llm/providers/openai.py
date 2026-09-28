"""OpenAI through Pydantic AI's Responses adapter, on an SDK client owned by bootstrap."""

from typing import override

import openai
from pydantic_ai import NativeOutput, ToolOutput
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings
from pydantic_ai.settings import ModelSettings

from app.llm.contracts import ModelProfile
from app.llm.provider import ModelProvider, OutputT


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
            # Keep prompts and responses out of OpenAI's stored-response history.
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

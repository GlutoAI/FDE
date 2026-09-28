"""The offline provider used by default runs and tests; it never makes a request."""

from typing import override

from pydantic_ai import NativeOutput, ToolOutput
from pydantic_ai.models import Model
from pydantic_ai.models.test import TestModel
from pydantic_ai.settings import ModelSettings

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

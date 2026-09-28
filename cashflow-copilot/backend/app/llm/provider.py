"""Application-owned boundary that hides every model vendor difference from agents."""

from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel
from pydantic_ai import NativeOutput, ToolOutput
from pydantic_ai.models import Model
from pydantic_ai.settings import ModelSettings

from app.llm.contracts import ModelProfile

OutputT = TypeVar("OutputT", bound=BaseModel)


class ModelProvider(ABC):
    """A configured model vendor: its model, settings, output mode, and SDK error codes.

    SDK clients are owned by bootstrap; implementations only wrap an initialized model.
    """

    @abstractmethod
    def get_model(self) -> Model:
        """Return the injected Pydantic AI model without making network requests.

        Returns:
            A model the shared runtime can call.
        """

    @abstractmethod
    def build_model_settings(self, profile: ModelProfile) -> ModelSettings:
        """Return shared request limits plus this vendor's own settings keys.

        Args:
            profile: Resolved timeout, output-token cap, and optional reasoning effort.

        Returns:
            Settings passed to every request of the runtime.

        Raises:
            ConfigurationError: The profile asks for a setting this vendor cannot honor.
        """

    @abstractmethod
    def build_output_spec(
        self, output_type: type[OutputT]
    ) -> NativeOutput[OutputT] | ToolOutput[OutputT]:
        """Return how the model must deliver structured output.

        Args:
            output_type: Pydantic schema the response must satisfy.

        Returns:
            Native JSON-schema output where the model supports it, tool output otherwise.
        """

    @abstractmethod
    def classify_sdk_error(self, error: BaseException | None) -> str | None:
        """Return a safe error code for this vendor's SDK transport failures.

        Args:
            error: An exception raised by, or chained from, the vendor SDK.

        Returns:
            ``timeout``, ``network``, or ``invalid_response`` when recognized; None when the
            error is not the SDK's.
        """

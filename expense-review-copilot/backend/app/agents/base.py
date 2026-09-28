"""Validate typed input before running Pydantic AI and return typed output with provenance."""

import asyncio
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel, ValidationError
from pydantic_ai import Agent
from pydantic_ai.run import AgentRunResult
from pydantic_ai.usage import UsageLimits

from app.core.errors import AgentInputError, AgentOutputError
from app.llm.contracts import AgentResult, LoadedPrompt, ModelProfile
from app.llm.provider import ModelProvider
from app.llm.runtime import normalize_model_errors

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class BaseAgent(ABC, Generic[InputT, OutputT]):
    """A typed single-call agent template with runtime, input type, and prompt injection."""

    def __init__(
        self,
        runtime: Agent[InputT, OutputT],
        provider: ModelProvider,
        prompt: LoadedPrompt,
        profile: ModelProfile,
        *,
        input_type: type[InputT],
    ) -> None:
        """Store initialized dependencies without I/O or model calls.

        Args:
            runtime: Centrally built Pydantic AI agent with an explicit output schema.
            provider: Vendor boundary the runtime was built from; classifies its SDK errors.
            prompt: Versioned YAML instructions and user message.
            profile: Resolved provider identity and invocation limits.
            input_type: Pydantic class enforcing the input contract before any model call.
        """
        self._runtime = runtime
        self._provider = provider
        self._prompt = prompt
        self._profile = profile
        self._input_type = input_type

    async def run_agent(self, request: InputT) -> AgentResult[OutputT]:
        """Validate input, run one Pydantic AI request, and validate the domain result.

        Args:
            request: Agent-specific Pydantic input; invalid payloads fail before inference.

        Returns:
            Validated model output with application-owned usage and prompt metadata.

        Raises:
            AgentInputError: Input violates the agent's Pydantic schema.
            ProviderError: Inference fails or exceeds its deadline.
            AgentOutputError: Output violates the schema or domain contract.
        """
        try:
            payload = request.model_dump() if isinstance(request, BaseModel) else request
            validated = self._input_type.model_validate(payload)
        except ValidationError as error:
            raise AgentInputError("invalid_input: request failed the agent contract") from error
        with normalize_model_errors(self._provider):
            async with asyncio.timeout(self._profile.timeout_seconds):
                result = await self._runtime.run(
                    self._prompt.template.user + "\n" + validated.model_dump_json(),
                    deps=validated,
                    usage_limits=UsageLimits(request_limit=1, tool_calls_limit=0),
                )
            self._validate_output(validated, result.output)
            return self._build_result(result)

    def _build_result(self, result: AgentRunResult[OutputT]) -> AgentResult[OutputT]:
        """Attach deterministic provenance and keep fixture/absent usage unknown."""
        response = result.response
        if self._profile.provider != "fixture" and (
            response.finish_reason != "stop" or not response.model_name
        ):
            raise AgentOutputError("invalid_output: provider did not complete its response")
        usage = result.usage
        has_usage = self._profile.provider != "fixture" and bool(
            usage.input_tokens or usage.output_tokens
        )
        return AgentResult[OutputT](
            output=result.output,
            provider=self._profile.provider,
            model_id=response.model_name or self._profile.model_id,
            prompt_version=self._prompt.template.version,
            prompt_sha256=self._prompt.sha256,
            input_tokens=usage.input_tokens if has_usage else None,
            output_tokens=usage.output_tokens if has_usage else None,
        )

    @abstractmethod
    def _validate_output(self, request: InputT, output: OutputT) -> None:
        """Raise AgentOutputError if schema-valid output violates input-dependent invariants."""

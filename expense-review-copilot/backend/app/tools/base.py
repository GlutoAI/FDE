"""The tool contract: a declared spec, typed arguments and result, and a bounded call.

A model chooses which tool to call and with which arguments; everything after that choice is
deterministic code. The tenant comes from the server-side ``ToolContext``, never from arguments.
"""

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Generic, TypeVar

from pydantic import BaseModel, Field, ValidationError

from app.core.context import TenantScope
from app.core.errors import ToolAccessError
from app.llm.contracts import Contract

ArgumentsT = TypeVar("ArgumentsT", bound=BaseModel)
ResultT = TypeVar("ResultT", bound=BaseModel)


class ToolSpec(Contract):
    """What a tool is called, what it does, and how it may run."""

    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$", description="Name the model calls")
    version: int = Field(ge=1, description="Incremented when arguments or results change")
    description: str = Field(min_length=1, max_length=1000, description="Shown to the model")
    is_read_only: bool = Field(description="True when the tool changes no state")
    timeout_seconds: float = Field(gt=0, le=30, description="Deadline for one call")


class ToolContext(Contract):
    """Server-side facts about who a call runs for; models cannot set any of it."""

    scope: TenantScope = Field(description="Tenant every read is restricted to")


class BaseTool(ABC, Generic[ArgumentsT, ResultT]):
    """A tool whose calls are validated, time-bounded, and typed end to end.

    Attributes:
        spec: Name, description, and limits.
        arguments_type: Contract the model's arguments must satisfy.
        result_type: Contract every result satisfies.
    """

    def __init__(
        self, spec: ToolSpec, arguments_type: type[ArgumentsT], result_type: type[ResultT]
    ) -> None:
        """Declare the tool; subclasses pass their constants and inject collaborators.

        Args:
            spec: Tool metadata and limits.
            arguments_type: Pydantic model describing the arguments.
            result_type: Pydantic model describing the result.
        """
        self.spec = spec
        self.arguments_type = arguments_type
        self.result_type = result_type

    async def call_tool(self, context: ToolContext, arguments: Mapping[str, object]) -> ResultT:
        """Validate the arguments, run the tool within its deadline, and return its result.

        Args:
            context: Server-side tenant and identity for this call.
            arguments: JSON arguments as sent by the model.

        Returns:
            The typed result.

        Raises:
            ToolAccessError: The arguments are invalid or the call exceeded its deadline.
            ExpenseError: A subclass raised by the tool, such as ``RecordNotFoundError``.
        """
        try:
            parsed = self.arguments_type.model_validate(arguments, strict=False)
        except ValidationError as error:
            raise ToolAccessError(f"invalid_arguments: {self.spec.name}") from error
        try:
            async with asyncio.timeout(self.spec.timeout_seconds):
                return await self._run_tool(context, parsed)
        except TimeoutError as error:
            raise ToolAccessError(f"timeout: {self.spec.name} exceeded its deadline") from error

    @abstractmethod
    async def _run_tool(self, context: ToolContext, arguments: ArgumentsT) -> ResultT:
        """Perform the tool's work for ``context.scope`` only.

        Implementations read or write nothing outside the context's tenant and raise a
        ``ExpenseError`` subclass with a safe message for any expected failure.
        """

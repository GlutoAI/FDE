"""Initial Pydantic AI connection agent; schema definitions live beside the implementation."""

from typing import override

from app.agents.base import BaseAgent
from app.agents.connection_models import ConnectionInput, ConnectionOutput
from app.core.errors import AgentOutputError


class ConnectionAgent(BaseAgent[ConnectionInput, ConnectionOutput]):
    """A no-tool diagnostic with explicit Pydantic input and native structured output."""

    @override
    def _validate_output(self, request: ConnectionInput, output: ConnectionOutput) -> None:
        if output.marker != request.expected_marker:
            raise AgentOutputError("unexpected_output: connection marker did not match the input")

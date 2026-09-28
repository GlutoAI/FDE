"""Explicit input and output contracts for the initial Pydantic AI connection agent."""

from typing import Literal

from pydantic import Field

from app.llm.contracts import Contract


class ConnectionInput(Contract):
    """A synthetic probe request; arbitrary business data is not accepted."""

    expected_marker: Literal["CONNECTION_OK"] = Field(
        default="CONNECTION_OK", description="Fixed diagnostic marker to return"
    )


class ConnectionOutput(Contract):
    """The schema Pydantic AI sends to the model and validates on its response."""

    status: Literal["ok"] = Field(description="Successful diagnostic response")
    marker: Literal["CONNECTION_OK"] = Field(description="Exact requested diagnostic marker")

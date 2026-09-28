"""Validated row contracts for tenant-owned tables; money is always integer cents."""

from datetime import date
from typing import ClassVar, Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from app.core.context import TENANT_ID_PATTERN
from app.llm.contracts import Contract

# Keys appear in paths, logs, and tool arguments, so they are restricted to a safe alphabet.
RECORD_KEY_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.-]*$"


class TenantRecord(Contract):
    """A row owned by exactly one tenant, identified within it by one key field.

    Attributes:
        key_field: Name of the field that is unique within a tenant.
    """

    key_field: ClassVar[str]

    tenant_id: str = Field(pattern=TENANT_ID_PATTERN, description="Owning tenant identifier")

    @property
    def record_key(self) -> str:
        """The value of this record's key field."""
        return str(getattr(self, self.key_field))


class ExampleRecord(TenantRecord):
    """The example record: one row of the first structured CSV a project imports.

    Replace it with the project's first real record type; the tables, CSV import, example tool,
    and tests follow its fields. It shows the patterns every record needs: a tenant-scoped key,
    integer cents, an optional field, and a cross-field rule in a model validator.
    """

    key_field: ClassVar[str] = "record_id"

    record_id: str = Field(pattern=RECORD_KEY_PATTERN, description="Record identifier")
    owner_id: str = Field(pattern=RECORD_KEY_PATTERN, description="Owning user ID")
    name: str = Field(min_length=1, max_length=200, description="Display name as exported")
    category: str = Field(min_length=1, max_length=64, description="Category as exported")
    amount_cents: int = Field(ge=0, description="Amount in integer cents")
    currency: Literal["USD"] = Field(description="Currency; only USD is modeled")
    opened_on: date = Field(description="Date the record was opened")
    closed_on: date | None = Field(description="Date it was closed; None while open")
    updated_at: AwareDatetime = Field(description="Last change in the source system")

    @model_validator(mode="after")
    def validate_dates(self) -> Self:
        """Reject records that close before they open.

        Returns:
            The record unchanged, as Pydantic requires of an ``after`` validator.

        Raises:
            ValueError: ``closed_on`` precedes ``opened_on``; Pydantic reports it as a
                ``ValidationError``.
        """
        if self.closed_on is not None and self.closed_on < self.opened_on:
            raise ValueError("closed_on cannot precede opened_on")
        return self

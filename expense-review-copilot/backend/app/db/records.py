"""Validated row contracts for tenant-owned tables; money is always integer cents."""

from datetime import date
from typing import ClassVar, Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from app.core.context import TENANT_ID_PATTERN
from app.llm.contracts import Contract

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


class ExpenseRecord(TenantRecord):
    """One submitted expense line from a card or reimbursement export.

    A missing ``receipt_id`` is data, not an error: finding such expenses is a product feature.
    """

    key_field: ClassVar[str] = "expense_id"

    expense_id: str = Field(pattern=RECORD_KEY_PATTERN, description="Expense identifier")
    submitted_by: str = Field(pattern=RECORD_KEY_PATTERN, description="Submitting user ID")
    merchant: str = Field(min_length=1, max_length=200, description="Merchant as exported")
    expense_date: date = Field(description="Date of the transaction")
    posted_date: date = Field(description="Date the transaction posted to the account")
    amount_cents: int = Field(gt=0, description="Charged amount; refunds are separate records")
    currency: Literal["USD"] = Field(description="Transaction currency; only USD is modeled")
    category: str = Field(min_length=1, max_length=64, description="Category as submitted")
    receipt_id: str | None = Field(
        pattern=RECORD_KEY_PATTERN, description="Attached receipt ID; None when missing"
    )
    updated_at: AwareDatetime = Field(description="Last change in the source system")

    @model_validator(mode="after")
    def validate_dates(self) -> Self:
        """Reject rows that post before the transaction happened."""
        if self.posted_date < self.expense_date:
            raise ValueError("posted_date cannot precede expense_date")
        return self

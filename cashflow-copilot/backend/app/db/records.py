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


class CustomerRecord(TenantRecord):
    """A customer billed by the tenant."""

    key_field: ClassVar[str] = "customer_id"

    customer_id: str = Field(pattern=RECORD_KEY_PATTERN, description="Customer identifier")
    display_name: str = Field(min_length=1, max_length=200, description="Business name")
    contact_name: str = Field(min_length=1, max_length=200, description="Billing contact")
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+$", description="Billing contact email")
    payment_terms_days: int = Field(ge=0, le=365, description="Net payment terms in days")
    currency: Literal["USD"] = Field(description="Billing currency; only USD is modeled")
    active: bool = Field(description="Whether the customer can still be invoiced")


class InvoiceRecord(TenantRecord):
    """An accounts-receivable invoice whose balances must be internally consistent."""

    key_field: ClassVar[str] = "invoice_id"

    invoice_id: str = Field(pattern=RECORD_KEY_PATTERN, description="Invoice identifier")
    customer_id: str = Field(pattern=RECORD_KEY_PATTERN, description="Billed customer")
    invoice_number: str = Field(min_length=1, description="Number shown to the customer")
    issue_date: date = Field(description="Date the invoice was issued")
    due_date: date = Field(description="Date payment is due")
    currency: Literal["USD"] = Field(description="Invoice currency; only USD is modeled")
    subtotal_cents: int = Field(ge=0, description="Amount before tax")
    tax_cents: int = Field(ge=0, description="Tax amount")
    total_cents: int = Field(ge=0, description="Subtotal plus tax")
    paid_cents: int = Field(ge=0, description="Amount received so far")
    balance_cents: int = Field(ge=0, description="Total minus paid")
    status: Literal["open", "partially_paid", "paid", "disputed"] = Field(
        description="Collection status"
    )
    disputed_cents: int = Field(ge=0, description="Amount under dispute")
    source_system: str = Field(min_length=1, description="System the record was imported from")
    external_id: str = Field(min_length=1, description="Identifier in the source system")
    updated_at: AwareDatetime = Field(description="Last change in the source system")

    @model_validator(mode="after")
    def validate_amounts(self) -> Self:
        """Reject rows whose totals, balances, or dates contradict each other."""
        if self.total_cents != self.subtotal_cents + self.tax_cents:
            raise ValueError("total_cents must equal subtotal_cents + tax_cents")
        if self.balance_cents != self.total_cents - self.paid_cents:
            raise ValueError("balance_cents must equal total_cents - paid_cents")
        if self.disputed_cents > self.balance_cents:
            raise ValueError("disputed_cents cannot exceed balance_cents")
        if self.due_date < self.issue_date:
            raise ValueError("due_date cannot precede issue_date")
        return self

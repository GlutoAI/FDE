"""Read-only finance tools over tenant-scoped repositories.

Results omit contact details: a customer's email is reserved for the trusted contact lookup
that later drafting phases add.
"""

from typing import override

from pydantic import Field

from app.db.records import RECORD_KEY_PATTERN, CustomerRecord, InvoiceRecord
from app.db.repository import MAX_LIST_LIMIT, RecordRepository
from app.llm.contracts import Contract
from app.tools.base import BaseTool, ToolContext, ToolSpec


class CustomerLookup(Contract):
    """Arguments naming one customer."""

    customer_id: str = Field(pattern=RECORD_KEY_PATTERN, description="Customer ID, e.g. CUS-A-001")


class CustomerSummary(Contract):
    """A customer's billing profile without contact details."""

    customer_id: str = Field(description="Customer ID")
    display_name: str = Field(description="Business name")
    payment_terms_days: int = Field(description="Net payment terms in days")
    active: bool = Field(description="Whether the customer can still be invoiced")


class CustomerInvoicesLookup(Contract):
    """Arguments for listing one customer's invoices."""

    customer_id: str = Field(pattern=RECORD_KEY_PATTERN, description="Customer ID, e.g. CUS-A-001")
    limit: int = Field(default=10, ge=1, le=20, description="Maximum invoices to return")


class InvoiceSummary(Contract):
    """An invoice's amounts and status; money is integer cents."""

    invoice_id: str = Field(description="Invoice ID")
    due_date: str = Field(description="Due date, ISO 8601")
    total_cents: int = Field(description="Invoice total")
    balance_cents: int = Field(description="Amount still owed")
    disputed_cents: int = Field(description="Amount under dispute")
    status: str = Field(description="open, partially_paid, paid, or disputed")


class InvoiceList(Contract):
    """Invoices returned by a lookup, newest due date first."""

    invoices: list[InvoiceSummary] = Field(description="Matching invoices; may be empty")


class GetCustomerTool(BaseTool[CustomerLookup, CustomerSummary]):
    """Return one customer of the calling tenant."""

    def __init__(self, repository: RecordRepository[CustomerRecord]) -> None:
        """Bind the tool to customer storage.

        Args:
            repository: Tenant-scoped customer records.
        """
        spec = ToolSpec(
            name="get_customer",
            version=1,
            description="Return a customer's name, payment terms, and status by customer ID.",
            is_read_only=True,
            timeout_seconds=5,
        )
        super().__init__(spec, CustomerLookup, CustomerSummary)
        self._repository = repository

    @override
    async def _run_tool(self, context: ToolContext, arguments: CustomerLookup) -> CustomerSummary:
        record = await self._repository.get_record(context.scope, arguments.customer_id)
        return CustomerSummary(
            customer_id=record.customer_id,
            display_name=record.display_name,
            payment_terms_days=record.payment_terms_days,
            active=record.active,
        )


class ListCustomerInvoicesTool(BaseTool[CustomerInvoicesLookup, InvoiceList]):
    """List one customer's invoices for the calling tenant."""

    def __init__(self, repository: RecordRepository[InvoiceRecord]) -> None:
        """Bind the tool to invoice storage.

        Args:
            repository: Tenant-scoped invoice records.
        """
        spec = ToolSpec(
            name="list_customer_invoices",
            version=1,
            description="List a customer's invoices with balances, newest due date first.",
            is_read_only=True,
            timeout_seconds=5,
        )
        super().__init__(spec, CustomerInvoicesLookup, InvoiceList)
        self._repository = repository

    @override
    async def _run_tool(
        self, context: ToolContext, arguments: CustomerInvoicesLookup
    ) -> InvoiceList:
        # Filtering in Python is sufficient for the synthetic corpus; add a query at scale.
        records = await self._repository.list_records(context.scope, limit=MAX_LIST_LIMIT)
        matching = sorted(
            (record for record in records if record.customer_id == arguments.customer_id),
            key=lambda record: record.due_date,
            reverse=True,
        )
        return InvoiceList(invoices=[_to_invoice_summary(r) for r in matching[: arguments.limit]])


def _to_invoice_summary(record: InvoiceRecord) -> InvoiceSummary:
    """Project an invoice record onto the fields the tool exposes."""
    return InvoiceSummary(
        invoice_id=record.invoice_id,
        due_date=record.due_date.isoformat(),
        total_cents=record.total_cents,
        balance_cents=record.balance_cents,
        disputed_cents=record.disputed_cents,
        status=record.status,
    )

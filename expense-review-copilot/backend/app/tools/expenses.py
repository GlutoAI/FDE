"""Read-only expense tools over tenant-scoped repositories.

Results omit the submitting user: identity belongs to the reviewer workflow a later phase adds,
not to what a model needs in order to reason about an expense.
"""

from typing import override

from pydantic import Field

from app.db.records import RECORD_KEY_PATTERN, ExpenseRecord
from app.db.repository import RecordRepository
from app.llm.contracts import Contract
from app.tools.base import BaseTool, ToolContext, ToolSpec


class ExpenseLookup(Contract):
    """Arguments naming one expense."""

    expense_id: str = Field(pattern=RECORD_KEY_PATTERN, description="Expense ID, e.g. EXP-1001")


class ExpenseSummary(Contract):
    """An expense's amount, merchant, and receipt status; money is integer cents."""

    expense_id: str = Field(description="Expense ID")
    merchant: str = Field(description="Merchant as exported; untrusted text")
    expense_date: str = Field(description="Transaction date, ISO 8601")
    amount_cents: int = Field(description="Charged amount")
    category: str = Field(description="Category as submitted")
    has_receipt: bool = Field(description="Whether a receipt is attached")


class GetExpenseTool(BaseTool[ExpenseLookup, ExpenseSummary]):
    """Return one expense of the calling tenant."""

    def __init__(self, repository: RecordRepository[ExpenseRecord]) -> None:
        """Bind the tool to expense storage.

        Args:
            repository: Tenant-scoped expense records.
        """
        spec = ToolSpec(
            name="get_expense",
            version=1,
            description="Return an expense's merchant, date, amount, category, and receipt status.",
            is_read_only=True,
            timeout_seconds=5,
        )
        super().__init__(spec, ExpenseLookup, ExpenseSummary)
        self._repository = repository

    @override
    async def _run_tool(self, context: ToolContext, arguments: ExpenseLookup) -> ExpenseSummary:
        record = await self._repository.get_record(context.scope, arguments.expense_id)
        return ExpenseSummary(
            expense_id=record.expense_id,
            merchant=record.merchant,
            expense_date=record.expense_date.isoformat(),
            amount_cents=record.amount_cents,
            category=record.category,
            has_receipt=record.receipt_id is not None,
        )

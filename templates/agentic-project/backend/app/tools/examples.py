"""The example read-only tool over tenant-scoped repositories.

Replace it with the project's first real tool. Results omit the owning user: a tool returns
only what the model needs to reason about the record, never identity it does not need.
"""

from typing import override

from pydantic import Field

from app.db.records import RECORD_KEY_PATTERN, ExampleRecord
from app.db.repository import RecordRepository
from app.llm.contracts import Contract
from app.tools.base import BaseTool, ToolContext, ToolSpec


class ExampleRecordLookup(Contract):
    """Arguments naming one record."""

    record_id: str = Field(pattern=RECORD_KEY_PATTERN, description="Record ID, e.g. REC-1001")


class ExampleRecordSummary(Contract):
    """A record's name, category, amount, and open status; money is integer cents."""

    record_id: str = Field(description="Record ID")
    name: str = Field(description="Display name as exported; untrusted text")
    category: str = Field(description="Category as exported")
    amount_cents: int = Field(description="Amount in integer cents")
    opened_on: str = Field(description="Date opened, ISO 8601")
    is_open: bool = Field(description="Whether the record is still open")


class GetExampleRecordTool(BaseTool[ExampleRecordLookup, ExampleRecordSummary]):
    """A read-only tool returning one of the calling tenant's records by ID.

    Another tenant's record with the same ID is reported as not found, exactly like a missing
    one, so the model cannot learn that it exists.
    """

    def __init__(self, repository: RecordRepository[ExampleRecord]) -> None:
        """Bind the tool to record storage.

        Args:
            repository: Tenant-scoped example records.
        """
        spec = ToolSpec(
            name="get_example_record",
            version=1,
            description="Return a record's name, category, amount, open date, and open status.",
            is_read_only=True,
            timeout_seconds=5,
        )
        super().__init__(spec, ExampleRecordLookup, ExampleRecordSummary)
        self._repository = repository

    @override
    async def _run_tool(
        self, context: ToolContext, arguments: ExampleRecordLookup
    ) -> ExampleRecordSummary:
        record = await self._repository.get_record(context.scope, arguments.record_id)
        return ExampleRecordSummary(
            record_id=record.record_id,
            name=record.name,
            category=record.category,
            amount_cents=record.amount_cents,
            opened_on=record.opened_on.isoformat(),
            is_open=record.closed_on is None,
        )

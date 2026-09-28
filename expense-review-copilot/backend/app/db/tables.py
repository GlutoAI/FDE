"""SQLAlchemy Core table definitions; every tenant-owned table keys on (tenant_id, id).

Composite keys and composite foreign keys stop a row in one tenant from referencing another
tenant's row. Schema creation uses ``metadata.create_all`` until migrations are introduced.
"""

from datetime import UTC, datetime
from typing import override

from sqlalchemy import (
    Column,
    Date,
    Dialect,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    TypeDecorator,
)
from sqlalchemy.types import JSON

KEY_LENGTH = 64

metadata = MetaData()


class UtcDateTime(TypeDecorator[datetime]):
    """A timezone-aware instant stored as UTC ISO-8601 text.

    SQLite has no timezone-aware type; text in one fixed UTC format keeps ordering correct and
    round-trips an aware datetime on every dialect.
    """

    impl = String(40)
    cache_ok = True

    @override
    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> str | None:
        """Convert an aware datetime to UTC text; reject naive values."""
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetimes are not stored")
        return value.astimezone(UTC).isoformat()

    @override
    def process_result_value(self, value: str | None, dialect: Dialect) -> datetime | None:
        """Parse stored UTC text back into an aware datetime."""
        return None if value is None else datetime.fromisoformat(value)


def _build_key_column(name: str) -> Column[str]:
    """Return a primary-key string column of the standard key length."""
    return Column(name, String(KEY_LENGTH), primary_key=True)


expenses = Table(
    "expenses",
    metadata,
    _build_key_column("tenant_id"),
    _build_key_column("expense_id"),
    Column("submitted_by", String(KEY_LENGTH), nullable=False),
    Column("merchant", String(200), nullable=False),
    Column("expense_date", Date, nullable=False),
    Column("posted_date", Date, nullable=False),
    Column("amount_cents", Integer, nullable=False),
    Column("currency", String(3), nullable=False),
    Column("category", String(64), nullable=False),
    Column("receipt_id", String(KEY_LENGTH), nullable=True),
    Column("updated_at", UtcDateTime, nullable=False),
)

memory_preferences = Table(
    "memory_preferences",
    metadata,
    _build_key_column("tenant_id"),
    _build_key_column("preference_id"),
    Column("expense_id", String(KEY_LENGTH), nullable=True),
    Column("key", String(64), nullable=False),
    Column("value", String(500), nullable=False),
    Column("approved_by", String(KEY_LENGTH), nullable=False),
    Column("status", String(16), nullable=False),
    Column("source", String(64), nullable=False),
    Column("created_at", UtcDateTime, nullable=False),
    Column("expires_at", UtcDateTime, nullable=True),
    ForeignKeyConstraint(
        ["tenant_id", "expense_id"], ["expenses.tenant_id", "expenses.expense_id"]
    ),
)

# thread_id is globally unique so each thread has exactly one owning tenant.
conversation_threads = Table(
    "conversation_threads",
    metadata,
    Column("thread_id", String(KEY_LENGTH), primary_key=True),
    Column("tenant_id", String(KEY_LENGTH), nullable=False),
)

conversation_messages = Table(
    "conversation_messages",
    metadata,
    Column(
        "thread_id",
        String(KEY_LENGTH),
        ForeignKey("conversation_threads.thread_id"),
        primary_key=True,
    ),
    Column("sequence", Integer, primary_key=True),
    Column("message", JSON, nullable=False),
)

# Vectors are JSON arrays searched exactly in Python; pgvector replaces this at scale.
document_chunks = Table(
    "document_chunks",
    metadata,
    _build_key_column("tenant_id"),
    Column("index_version", String(200), primary_key=True),
    _build_key_column("chunk_id"),
    Column("document_id", String(KEY_LENGTH), nullable=False),
    Column("ordinal", Integer, nullable=False),
    Column("text", Text, nullable=False),
    Column("vector", JSON, nullable=False),
    Index("ix_document_chunks_document", "tenant_id", "index_version", "document_id"),
)

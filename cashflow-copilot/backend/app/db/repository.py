"""Tenant-scoped record storage: the repository contract, an in-memory fake, and SQL storage.

Every read takes a ``TenantScope``; no method accepts free-form SQL or a tenant chosen by a model.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Generic, TypeVar, override

from sqlalchemy import ColumnElement, Executable, Table, and_, insert, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from app.core.context import TenantScope
from app.core.errors import InvalidQueryError, RecordNotFoundError, StorageError
from app.db.records import TenantRecord

RecordT = TypeVar("RecordT", bound=TenantRecord)

MAX_LIST_LIMIT = 500


class RecordRepository(ABC, Generic[RecordT]):
    """Storage for one tenant-owned record type."""

    @abstractmethod
    async def save_records(self, records: Sequence[RecordT]) -> int:
        """Insert new records and replace existing ones with the same tenant and key.

        The write is atomic: either every record is saved or none is. Saving the same records
        again leaves storage unchanged.

        Args:
            records: Records to write; may belong to several tenants.

        Returns:
            The number of records written.

        Raises:
            StorageError: The write failed, for example on a missing referenced row.
        """

    @abstractmethod
    async def get_record(self, scope: TenantScope, record_key: str) -> RecordT:
        """Return the tenant's record with the given key.

        Args:
            scope: Tenant the caller acts for.
            record_key: Value of the record type's key field.

        Returns:
            The stored record.

        Raises:
            RecordNotFoundError: The tenant has no such record, including when another
                tenant owns a record with that key.
            StorageError: The read failed.
        """

    @abstractmethod
    async def list_records(self, scope: TenantScope, *, limit: int) -> list[RecordT]:
        """Return up to ``limit`` of the tenant's records, ordered by key.

        Args:
            scope: Tenant the caller acts for.
            limit: Maximum rows, from 1 to ``MAX_LIST_LIMIT``.

        Returns:
            A possibly empty list containing only that tenant's records.

        Raises:
            InvalidQueryError: ``limit`` is outside the allowed range.
            StorageError: The read failed.
        """


class InMemoryRecordRepository(RecordRepository[RecordT]):
    """A dictionary-backed repository for tests; honors the same contract as SQL storage."""

    def __init__(self) -> None:
        """Start with no records."""
        self._record_by_key: dict[tuple[str, str], RecordT] = {}

    @override
    async def save_records(self, records: Sequence[RecordT]) -> int:
        for record in records:
            self._record_by_key[(record.tenant_id, record.record_key)] = record
        return len(records)

    @override
    async def get_record(self, scope: TenantScope, record_key: str) -> RecordT:
        record = self._record_by_key.get((scope.tenant_id, record_key))
        if record is None:
            raise RecordNotFoundError(f"record_not_found: {record_key}")
        return record

    @override
    async def list_records(self, scope: TenantScope, *, limit: int) -> list[RecordT]:
        validate_list_limit(limit)
        owned = [
            record
            for (tenant_id, _), record in self._record_by_key.items()
            if tenant_id == scope.tenant_id
        ]
        return sorted(owned, key=lambda record: record.record_key)[:limit]


class SqlRecordRepository(RecordRepository[RecordT]):
    """Records stored in one SQL table whose columns match the record's fields."""

    def __init__(self, engine: AsyncEngine, table: Table, record_type: type[RecordT]) -> None:
        """Bind the repository to a table without opening a connection.

        Args:
            engine: Engine whose lifetime the caller owns.
            table: Table keyed on ``tenant_id`` plus the record type's key field.
            record_type: Contract used to validate every row read back.
        """
        self._engine = engine
        self._table = table
        self._record_type = record_type

    @override
    async def save_records(self, records: Sequence[RecordT]) -> int:
        try:
            async with self._engine.begin() as connection:
                for record in records:
                    await self._save_record(connection, record)
        except IntegrityError as error:
            raise StorageError("integrity_violation: a referenced row is missing") from error
        except SQLAlchemyError as error:
            raise StorageError("storage_failed: could not save records") from error
        return len(records)

    @override
    async def get_record(self, scope: TenantScope, record_key: str) -> RecordT:
        statement = select(self._table).where(self._match_key(scope.tenant_id, record_key))
        rows = await self._read_rows(statement)
        if not rows:
            raise RecordNotFoundError(f"record_not_found: {record_key}")
        return rows[0]

    @override
    async def list_records(self, scope: TenantScope, *, limit: int) -> list[RecordT]:
        validate_list_limit(limit)
        key_column = self._table.c[self._record_type.key_field]
        statement = (
            select(self._table)
            .where(self._table.c.tenant_id == scope.tenant_id)
            .order_by(key_column)
            .limit(limit)
        )
        return await self._read_rows(statement)

    async def _save_record(self, connection: AsyncConnection, record: RecordT) -> None:
        """Update the row with this record's tenant and key, or insert it when absent."""
        values = record.model_dump()
        match_key = self._match_key(record.tenant_id, record.record_key)
        result = await connection.execute(update(self._table).where(match_key).values(values))
        if result.rowcount == 0:
            await connection.execute(insert(self._table).values(values))

    async def _read_rows(self, statement: Executable) -> list[RecordT]:
        """Execute a select and validate each row against the record contract."""
        try:
            async with self._engine.connect() as connection:
                result = await connection.execute(statement)
                return [self._record_type.model_validate(dict(row._mapping)) for row in result]
        except SQLAlchemyError as error:
            raise StorageError("storage_failed: could not read records") from error

    def _match_key(self, tenant_id: str, record_key: str) -> ColumnElement[bool]:
        """Return the SQL condition selecting one tenant's row by key."""
        key_column = self._table.c[self._record_type.key_field]
        return and_(self._table.c.tenant_id == tenant_id, key_column == record_key)


def validate_list_limit(limit: int) -> None:
    """Raise when a list request is unbounded or empty.

    Args:
        limit: Requested maximum rows.

    Raises:
        InvalidQueryError: ``limit`` is below 1 or above ``MAX_LIST_LIMIT``.
    """
    if not 1 <= limit <= MAX_LIST_LIMIT:
        raise InvalidQueryError(f"invalid_limit: use 1 to {MAX_LIST_LIMIT}")

"""Conversation history per thread, stored in Pydantic AI's message format.

Each thread belongs to exactly one tenant. History is context, not a record of facts: balances
and permissions are always re-read from their sources rather than trusted from old messages.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import override

from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
from sqlalchemy import func, insert, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from app.core.context import TenantScope
from app.core.errors import AccessDeniedError, InvalidQueryError, StorageError
from app.db.tables import conversation_messages, conversation_threads

MAX_HISTORY_MESSAGES = 200


class ConversationStore(ABC):
    """Append-only message history for tenant-owned conversation threads."""

    @abstractmethod
    async def save_messages(
        self, scope: TenantScope, thread_id: str, messages: Sequence[ModelMessage]
    ) -> int:
        """Append messages to a thread, creating it for the tenant on first save.

        Args:
            scope: Tenant the caller acts for; it becomes the owner of a new thread.
            thread_id: Backend-issued thread identifier.
            messages: Messages in the order they occurred, for example ``result.new_messages()``.

        Returns:
            The number of messages appended.

        Raises:
            AccessDeniedError: Another tenant owns the thread.
            StorageError: The write failed; nothing was appended.
        """

    @abstractmethod
    async def load_messages(
        self, scope: TenantScope, thread_id: str, *, limit: int
    ) -> list[ModelMessage]:
        """Return the thread's most recent messages, oldest first.

        A bounded window can begin with a tool result whose call was cut off; callers that pass
        history to a model should start the window at a user request.

        Args:
            scope: Tenant the caller acts for.
            thread_id: Thread to read.
            limit: Maximum messages, from 1 to ``MAX_HISTORY_MESSAGES``.

        Returns:
            Up to ``limit`` messages in chronological order; empty for an unknown thread.

        Raises:
            AccessDeniedError: Another tenant owns the thread.
            InvalidQueryError: ``limit`` is outside the allowed range.
            StorageError: The read failed.
        """


class InMemoryConversationStore(ConversationStore):
    """A dictionary-backed conversation store for tests."""

    def __init__(self) -> None:
        """Start with no threads."""
        self._owner_by_thread: dict[str, str] = {}
        self._messages_by_thread: dict[str, list[ModelMessage]] = {}

    @override
    async def save_messages(
        self, scope: TenantScope, thread_id: str, messages: Sequence[ModelMessage]
    ) -> int:
        validate_thread_owner(self._owner_by_thread.get(thread_id), scope)
        self._owner_by_thread[thread_id] = scope.tenant_id
        self._messages_by_thread.setdefault(thread_id, []).extend(messages)
        return len(messages)

    @override
    async def load_messages(
        self, scope: TenantScope, thread_id: str, *, limit: int
    ) -> list[ModelMessage]:
        validate_history_limit(limit)
        validate_thread_owner(self._owner_by_thread.get(thread_id), scope)
        return self._messages_by_thread.get(thread_id, [])[-limit:]


class SqlConversationStore(ConversationStore):
    """Threads and JSON-serialized messages in the conversation tables."""

    def __init__(self, engine: AsyncEngine) -> None:
        """Bind to an engine whose lifetime the caller owns.

        Args:
            engine: Database containing the conversation tables.
        """
        self._engine = engine

    @override
    async def save_messages(
        self, scope: TenantScope, thread_id: str, messages: Sequence[ModelMessage]
    ) -> int:
        payloads = ModelMessagesTypeAdapter.dump_python(list(messages), mode="json")
        try:
            async with self._engine.begin() as connection:
                await self._ensure_thread_owner(connection, scope, thread_id)
                start = await self._find_next_sequence(connection, thread_id)
                if payloads:
                    rows = [
                        {"thread_id": thread_id, "sequence": start + offset, "message": payload}
                        for offset, payload in enumerate(payloads)
                    ]
                    await connection.execute(insert(conversation_messages), rows)
        except SQLAlchemyError as error:
            raise StorageError("storage_failed: could not save conversation messages") from error
        return len(payloads)

    @override
    async def load_messages(
        self, scope: TenantScope, thread_id: str, *, limit: int
    ) -> list[ModelMessage]:
        validate_history_limit(limit)
        table = conversation_messages
        statement = (
            select(table.c.message)
            .where(table.c.thread_id == thread_id)
            .order_by(table.c.sequence.desc())
            .limit(limit)
        )
        try:
            async with self._engine.connect() as connection:
                validate_thread_owner(await self._find_owner(connection, thread_id), scope)
                payloads: list[object] = list((await connection.execute(statement)).scalars())
        except SQLAlchemyError as error:
            raise StorageError("storage_failed: could not load conversation messages") from error
        return ModelMessagesTypeAdapter.validate_python(list(reversed(payloads)))

    async def _ensure_thread_owner(
        self, connection: AsyncConnection, scope: TenantScope, thread_id: str
    ) -> None:
        """Create the thread for the tenant if new; raise if another tenant owns it."""
        owner = await self._find_owner(connection, thread_id)
        validate_thread_owner(owner, scope)
        if owner is None:
            await connection.execute(
                insert(conversation_threads).values(thread_id=thread_id, tenant_id=scope.tenant_id)
            )

    async def _find_owner(self, connection: AsyncConnection, thread_id: str) -> str | None:
        """Return the owning tenant of a thread, or None when the thread does not exist."""
        table = conversation_threads
        return await connection.scalar(
            select(table.c.tenant_id).where(table.c.thread_id == thread_id)
        )

    async def _find_next_sequence(self, connection: AsyncConnection, thread_id: str) -> int:
        """Return the sequence number the next message in the thread receives."""
        table = conversation_messages
        highest = await connection.scalar(
            select(func.max(table.c.sequence)).where(table.c.thread_id == thread_id)
        )
        return 0 if highest is None else int(highest) + 1


def validate_thread_owner(owner_tenant_id: str | None, scope: TenantScope) -> None:
    """Raise when a thread exists and belongs to a different tenant.

    Args:
        owner_tenant_id: Current owner, or None for a thread that does not exist yet.
        scope: Tenant the caller acts for.

    Raises:
        AccessDeniedError: The thread belongs to another tenant.
    """
    if owner_tenant_id is not None and owner_tenant_id != scope.tenant_id:
        raise AccessDeniedError("access_denied: thread belongs to another tenant")


def validate_history_limit(limit: int) -> None:
    """Raise when a history read is unbounded or empty.

    Args:
        limit: Requested maximum messages.

    Raises:
        InvalidQueryError: ``limit`` is below 1 or above ``MAX_HISTORY_MESSAGES``.
    """
    if not 1 <= limit <= MAX_HISTORY_MESSAGES:
        raise InvalidQueryError(f"invalid_limit: use 1 to {MAX_HISTORY_MESSAGES}")

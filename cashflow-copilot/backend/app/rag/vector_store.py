"""Store embedded chunks and return the nearest ones, filtering by tenant before ranking.

The tenant and index-version filter runs before any similarity is computed, so another
tenant's text can never be ranked, returned, or leak through scores.
"""

import math
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import override

from sqlalchemy import and_, delete, insert, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.context import TenantScope
from app.core.errors import InvalidQueryError, StorageError
from app.db.tables import document_chunks
from app.rag.contracts import DocumentChunk, EmbeddedChunk, ScoredChunk, VectorQuery


class VectorStore(ABC):
    """Tenant-scoped storage of chunk vectors with exact nearest-neighbour search."""

    @abstractmethod
    async def replace_document_chunks(
        self, scope: TenantScope, document_id: str, chunks: Sequence[EmbeddedChunk]
    ) -> int:
        """Atomically replace one document's chunks within each given index version.

        Chunks of the document under the same index version that are not in ``chunks`` are
        removed, so re-ingesting a changed document leaves no stale passages.

        Args:
            scope: Tenant owning the document.
            document_id: Document whose chunks are replaced.
            chunks: New chunks; every one must belong to ``scope`` and ``document_id``.

        Returns:
            The number of chunks stored.

        Raises:
            InvalidQueryError: A chunk belongs to another tenant or document, or ``chunks``
                is empty.
            StorageError: The write failed; nothing changed.
        """

    @abstractmethod
    async def list_nearest_chunks(
        self, scope: TenantScope, query: VectorQuery
    ) -> list[ScoredChunk]:
        """Return the tenant's chunks most similar to the query vector, best first.

        Args:
            scope: Tenant the caller acts for; no other tenant's chunks are considered.
            query: Query vector, index version, and result limit.

        Returns:
            Up to ``query.limit`` chunks ordered by descending cosine similarity, ties broken
            by chunk ID; empty when the tenant has nothing indexed under that version.

        Raises:
            StorageError: The read failed.
        """


class InMemoryVectorStore(VectorStore):
    """A list-backed vector store for tests; same filtering and ordering as SQL storage."""

    def __init__(self) -> None:
        """Start with no chunks."""
        self._chunks: list[EmbeddedChunk] = []

    @override
    async def replace_document_chunks(
        self, scope: TenantScope, document_id: str, chunks: Sequence[EmbeddedChunk]
    ) -> int:
        validate_chunk_ownership(scope, document_id, chunks)
        versions = {chunk.index_version for chunk in chunks}
        self._chunks = [
            stored
            for stored in self._chunks
            if not _is_replaced(stored, scope, document_id, versions)
        ]
        self._chunks.extend(chunks)
        return len(chunks)

    @override
    async def list_nearest_chunks(
        self, scope: TenantScope, query: VectorQuery
    ) -> list[ScoredChunk]:
        candidates = [
            (stored.chunk, stored.vector)
            for stored in self._chunks
            if stored.chunk.tenant_id == scope.tenant_id
            and stored.index_version == query.index_version
        ]
        return rank_chunks(candidates, query)


class SqlVectorStore(VectorStore):
    """Chunks and JSON vectors in the ``document_chunks`` table, ranked exactly in Python."""

    def __init__(self, engine: AsyncEngine) -> None:
        """Bind to an engine whose lifetime the caller owns.

        Args:
            engine: Database containing the ``document_chunks`` table.
        """
        self._engine = engine

    @override
    async def replace_document_chunks(
        self, scope: TenantScope, document_id: str, chunks: Sequence[EmbeddedChunk]
    ) -> int:
        validate_chunk_ownership(scope, document_id, chunks)
        versions = sorted({chunk.index_version for chunk in chunks})
        rows = [_to_chunk_row(chunk) for chunk in chunks]
        table = document_chunks
        try:
            async with self._engine.begin() as connection:
                await connection.execute(
                    delete(table).where(
                        and_(
                            table.c.tenant_id == scope.tenant_id,
                            table.c.document_id == document_id,
                            table.c.index_version.in_(versions),
                        )
                    )
                )
                await connection.execute(insert(table), rows)
        except SQLAlchemyError as error:
            raise StorageError("storage_failed: could not replace document chunks") from error
        return len(rows)

    @override
    async def list_nearest_chunks(
        self, scope: TenantScope, query: VectorQuery
    ) -> list[ScoredChunk]:
        table = document_chunks
        statement = select(table).where(
            and_(table.c.tenant_id == scope.tenant_id, table.c.index_version == query.index_version)
        )
        try:
            async with self._engine.connect() as connection:
                rows = (await connection.execute(statement)).mappings().all()
        except SQLAlchemyError as error:
            raise StorageError("storage_failed: could not search chunks") from error
        candidates = [(_from_chunk_row(dict(row)), list(row["vector"])) for row in rows]
        return rank_chunks(candidates, query)


def validate_chunk_ownership(
    scope: TenantScope, document_id: str, chunks: Sequence[EmbeddedChunk]
) -> None:
    """Raise unless every chunk belongs to the tenant and document being replaced.

    Args:
        scope: Tenant owning the document.
        document_id: Document being replaced.
        chunks: Chunks to store.

    Raises:
        InvalidQueryError: ``chunks`` is empty or contains a foreign chunk.
    """
    if not chunks:
        raise InvalidQueryError("invalid_chunks: a document needs at least one chunk")
    for stored in chunks:
        if (stored.chunk.tenant_id, stored.chunk.document_id) != (scope.tenant_id, document_id):
            raise InvalidQueryError("invalid_chunks: chunk belongs to another tenant or document")


def rank_chunks(
    candidates: Sequence[tuple[DocumentChunk, list[float]]], query: VectorQuery
) -> list[ScoredChunk]:
    """Score already-filtered candidates by cosine similarity and keep the best.

    Args:
        candidates: Chunks and vectors of one tenant and index version.
        query: Query vector and limit.

    Returns:
        Up to ``query.limit`` scored chunks, best first, ties broken by chunk ID.
    """
    scored = [
        ScoredChunk(chunk=chunk, score=calculate_cosine_similarity(query.vector, vector))
        for chunk, vector in candidates
    ]
    scored.sort(key=lambda item: (-item.score, item.chunk.chunk_id))
    return scored[: query.limit]


def calculate_cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    """Return the cosine similarity of two vectors, clamped to [-1, 1].

    Args:
        left: First vector.
        right: Second vector of the same length.

    Returns:
        The similarity; 0.0 when either vector has zero length or the lengths differ.
    """
    if len(left) != len(right):
        return 0.0
    norm = math.sqrt(sum(a * a for a in left)) * math.sqrt(sum(b * b for b in right))
    if norm == 0:
        return 0.0
    return max(-1.0, min(1.0, sum(a * b for a, b in zip(left, right, strict=True)) / norm))


def _is_replaced(
    stored: EmbeddedChunk, scope: TenantScope, document_id: str, versions: set[str]
) -> bool:
    """Return whether a stored chunk is superseded by a replacement of its document."""
    return (
        stored.chunk.tenant_id == scope.tenant_id
        and stored.chunk.document_id == document_id
        and stored.index_version in versions
    )


def _to_chunk_row(stored: EmbeddedChunk) -> dict[str, object]:
    """Flatten an embedded chunk into ``document_chunks`` column values."""
    return stored.chunk.model_dump(exclude={"trust_level"}) | {
        "index_version": stored.index_version,
        "vector": stored.vector,
    }


def _from_chunk_row(row: dict[str, object]) -> DocumentChunk:
    """Rebuild a chunk contract from a ``document_chunks`` row."""
    fields = {
        name: row[name] for name in ("chunk_id", "tenant_id", "document_id", "ordinal", "text")
    }
    return DocumentChunk.model_validate(fields)

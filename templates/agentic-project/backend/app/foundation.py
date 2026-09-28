"""Compose storage, retrieval, memory, and tool configuration once at startup.

This is a composition root: it names concrete classes so everything else can depend on the
abstractions. Opening the foundation validates configuration, creates the database schema, and
opens clients; it sends no model or embedding request.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine

from app.bootstrap import open_embedder
from app.core.clock import Clock, SystemClock
from app.core.settings import ProjectLocation, Settings, load_embedding_profile
from app.db.csv_import import ImportReport, import_structured_data
from app.db.engine import build_database_url, open_database
from app.db.records import ExampleRecord
from app.db.repository import RecordRepository, SqlRecordRepository
from app.db.tables import example_records, memory_preferences
from app.mcp.client import MCPCatalog, load_mcp_catalog
from app.memory.conversation import ConversationStore, SqlConversationStore
from app.memory.preferences import (
    MemoryPreference,
    PreferenceMemory,
    load_preference_records,
)
from app.rag.embedder import BaseEmbedder
from app.rag.retriever import Retriever
from app.rag.vector_store import SqlVectorStore, VectorStore

PREFERENCES_FILE = "preferences.json"


@dataclass(frozen=True)
class Foundation:
    """Shared collaborators created at startup; their lifetimes end with ``open_foundation``.

    Attributes:
        location: Project root.
        engine: Open database engine.
        database_url: URL the engine uses; passed to MCP servers and never printed.
        clock: Time source for expiry and timestamps.
        example_records: The example record type; replace with the project's records.
        preference_records: Stored preferences, including inactive ones.
        preferences: Active-preference reader for agents.
        conversations: Conversation history per thread.
        embedder: Embedding model of the selected profile.
        vector_store: Chunk vectors.
        retriever: Tenant-scoped semantic search.
        mcp_catalog: Approved MCP servers and role allowlists.
    """

    location: ProjectLocation
    engine: AsyncEngine
    database_url: str = field(repr=False)
    clock: Clock
    example_records: RecordRepository[ExampleRecord]
    preference_records: RecordRepository[MemoryPreference]
    preferences: PreferenceMemory
    conversations: ConversationStore
    embedder: BaseEmbedder
    vector_store: VectorStore
    retriever: Retriever
    mcp_catalog: MCPCatalog


@asynccontextmanager
async def open_foundation(
    location: ProjectLocation, settings: Settings, *, clock: Clock | None = None
) -> AsyncIterator[Foundation]:
    """Validate configuration, open the database and embedder, and build every collaborator.

    Args:
        location: Project root containing backend/config/ and data/.
        settings: Validated settings; ``model_mode`` selects fixture or hosted embeddings.
        clock: Time source; the system clock when omitted.

    Yields:
        The composed foundation; the engine and embedding client close on exit.

    Raises:
        ConfigurationError: A catalog is invalid or a required key is missing.
        StorageError: The database cannot be opened.
    """
    mcp_catalog = load_mcp_catalog(location)
    embedding_profile = load_embedding_profile(location, settings)
    configured_url = settings.database_url.get_secret_value() if settings.database_url else None
    database_url = build_database_url(location.state_dir, configured_url)
    async with (
        open_database(database_url) as engine,
        open_embedder(embedding_profile, settings) as embedder,
    ):
        yield build_foundation(
            location,
            engine=engine,
            database_url=database_url,
            embedder=embedder,
            clock=clock or SystemClock(),
            mcp_catalog=mcp_catalog,
        )


async def import_seed_data(foundation: Foundation, directory: Path) -> list[ImportReport]:
    """Load one import directory's CSVs and optional preferences; safe to rerun.

    Every source is validated before the first write.

    Args:
        foundation: Open foundation whose database receives the data.
        directory: Import directory, e.g. ``data/raw/<source>/<date>/``, holding the files in
            ``STRUCTURED_SOURCES`` and optionally ``preferences.json``.

    Returns:
        One report per source, in import order.

    Raises:
        DataImportError: A source file is invalid; nothing is written.
        StorageError: A write failed.
    """
    preferences_path = directory / PREFERENCES_FILE
    has_preferences = preferences_path.exists()
    preferences = load_preference_records(preferences_path) if has_preferences else []
    reports = await import_structured_data(directory, foundation.engine)
    if has_preferences:
        written = await foundation.preference_records.save_records(preferences)
        reports.append(
            ImportReport(
                table=memory_preferences.name,
                source=PREFERENCES_FILE,
                rows_read=len(preferences),
                rows_written=written,
            )
        )
    return reports


def build_foundation(
    location: ProjectLocation,
    *,
    engine: AsyncEngine,
    database_url: str,
    embedder: BaseEmbedder,
    clock: Clock,
    mcp_catalog: MCPCatalog,
) -> Foundation:
    """Assemble repositories, memory, and retrieval over already-open resources, without I/O.

    Args:
        location: Project root.
        engine: Open database engine.
        database_url: URL of that engine.
        embedder: Open embedder.
        clock: Time source.
        mcp_catalog: Validated MCP catalog.

    Returns:
        The composed foundation.
    """
    preference_records = SqlRecordRepository(engine, memory_preferences, MemoryPreference)
    vector_store = SqlVectorStore(engine)
    return Foundation(
        location=location,
        engine=engine,
        database_url=database_url,
        clock=clock,
        example_records=SqlRecordRepository(engine, example_records, ExampleRecord),
        preference_records=preference_records,
        preferences=PreferenceMemory(preference_records, clock),
        conversations=SqlConversationStore(engine),
        embedder=embedder,
        vector_store=vector_store,
        retriever=Retriever(embedder, vector_store),
        mcp_catalog=mcp_catalog,
    )

"""Own the async database engine lifetime and create the schema at startup.

The default is a local SQLite file; a PostgreSQL URL (``postgresql+asyncpg://``) selects that
dialect later without changing repositories.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from sqlite3 import Connection as SqliteConnection

from sqlalchemy import event, make_url
from sqlalchemy.exc import ArgumentError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import ConnectionPoolEntry

from app.core.errors import ConfigurationError, StorageError
from app.db.tables import metadata

DEFAULT_DATABASE_NAME = "app.db"


def build_database_url(state_dir: Path, configured_url: str | None) -> str:
    """Return the configured URL, or the default SQLite file in the runtime state directory.

    Args:
        state_dir: Ignored local state directory, ``backend/data/`` in a project.
        configured_url: Explicit SQLAlchemy async URL from settings, if any.

    Returns:
        An async SQLAlchemy URL; nothing is opened here.
    """
    if configured_url:
        return configured_url
    return f"sqlite+aiosqlite:///{state_dir / DEFAULT_DATABASE_NAME}"


@asynccontextmanager
async def open_database(database_url: str) -> AsyncIterator[AsyncEngine]:
    """Create the engine, ensure the schema exists, and dispose of the engine on exit.

    Args:
        database_url: Async SQLAlchemy URL; SQLite parents are created if missing.

    Yields:
        A ready engine with every table in ``metadata`` created.

    Raises:
        ConfigurationError: The URL is malformed or names an uninstalled driver.
        StorageError: The database cannot be opened or the schema cannot be created.
    """
    engine = _create_engine(database_url)
    try:
        await ensure_database_schema(engine)
        yield engine
    finally:
        await engine.dispose()


async def ensure_database_schema(engine: AsyncEngine) -> None:
    """Create any missing tables; existing tables and rows are left unchanged.

    Args:
        engine: Engine for the target database.

    Raises:
        StorageError: The schema could not be created.
    """
    try:
        async with engine.begin() as connection:
            await connection.run_sync(metadata.create_all)
    except SQLAlchemyError as error:
        raise StorageError("storage_unavailable: could not create the database schema") from error


def _create_engine(database_url: str) -> AsyncEngine:
    """Build the engine; for SQLite, create the file's directory and enforce foreign keys.

    Args:
        database_url: Async SQLAlchemy URL.

    Returns:
        An engine with no connection opened yet.

    Raises:
        ConfigurationError: The URL is malformed or names an uninstalled driver. The message
            names the variable, never the URL, which may embed a password.
    """
    try:
        url = make_url(database_url)
        engine = create_async_engine(url)
    except (ArgumentError, ImportError, ValueError) as error:
        raise ConfigurationError("invalid_database_url: check TEMPLATE_DATABASE_URL") from error
    if url.get_backend_name() == "sqlite":
        if url.database and url.database != ":memory:":
            Path(url.database).parent.mkdir(parents=True, exist_ok=True)
        event.listen(engine.sync_engine, "connect", _enable_sqlite_foreign_keys)
    return engine


def _enable_sqlite_foreign_keys(
    dbapi_connection: SqliteConnection, connection_record: ConnectionPoolEntry
) -> None:
    """Turn on SQLite foreign-key enforcement, which is off by default per connection.

    Registered as a SQLAlchemy ``connect`` listener, so it runs once per new connection.

    Args:
        dbapi_connection: The raw ``sqlite3`` connection just opened.
        connection_record: Pool bookkeeping for that connection; unused.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

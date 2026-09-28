"""FastAPI access to the database engine the application lifespan opens.

Repositories and schema live in ``app.db``; this module only hands routes the shared engine and
checks that it answers.
"""

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine


def get_engine(request: Request) -> AsyncEngine:
    """Return the engine stored on the application at startup.

    Args:
        request: Current request, whose application state holds the engine.

    Returns:
        The shared async engine.
    """
    engine: AsyncEngine = request.app.state.engine
    return engine


async def check_database_connection(engine: AsyncEngine) -> bool:
    """Report whether the database answers a trivial query.

    Args:
        engine: Engine to probe.

    Returns:
        True when ``SELECT 1`` succeeds; False on any database or I/O failure.
    """
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError):
        return False
    return True

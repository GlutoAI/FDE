"""Create the FastAPI application; startup opens the database, never a model client.

Run from ``backend/`` with ``uvicorn app.main:app --reload``.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.settings import DEFAULT_PROJECT_ROOT, ProjectLocation, load_settings
from app.db.engine import build_database_url, open_database
from app.routers import diagnostics, health

FRONTEND_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]


def create_app(location: ProjectLocation) -> FastAPI:
    """Build the API for one project; settings and the database open when it starts.

    Args:
        location: Project whose ``.env``, ``backend/config/``, and ``backend/data/`` are used.

    Returns:
        An application with CORS for the local frontend and the health and diagnostics routes.
    """

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        """Load settings and hold one database engine for the application's lifetime."""
        settings = load_settings(location)
        configured = settings.database_url.get_secret_value() if settings.database_url else None
        async with open_database(build_database_url(location.state_dir, configured)) as engine:
            application.state.location = location
            application.state.settings = settings
            application.state.engine = engine
            yield

    application = FastAPI(title="Expense Review Copilot API", lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=FRONTEND_ORIGINS,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    application.include_router(health.router)
    application.include_router(diagnostics.router)
    return application


app = create_app(ProjectLocation(root=DEFAULT_PROJECT_ROOT))

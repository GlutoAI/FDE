"""Create the FastAPI application; startup opens the database, never a model client.

Run from ``backend/`` with ``uvicorn app.main:app --reload``.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import partial

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.settings import DEFAULT_PROJECT_ROOT, ProjectLocation, load_settings
from app.db.engine import build_database_url, open_database
from app.routers import diagnostics, health

# The Vite dev server and the Compose UI. Both normally proxy /api on their own origin, so
# CORS matters only when a page calls http://localhost:8000 directly.
FRONTEND_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]


def create_app(location: ProjectLocation) -> FastAPI:
    """Build the API for one project; settings and the database open when it starts.

    Args:
        location: Project whose ``.env``, ``backend/config/``, and ``backend/data/`` are used.

    Returns:
        An application with CORS for the local frontend and the health and diagnostics routes.
    """
    application = FastAPI(
        title="Agentic Project Template API", lifespan=partial(_open_app_resources, location)
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=FRONTEND_ORIGINS,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    application.include_router(health.router)
    application.include_router(diagnostics.router)
    return application


@asynccontextmanager
async def _open_app_resources(
    location: ProjectLocation, application: FastAPI
) -> AsyncIterator[None]:
    """Load settings and hold one database engine for the application's lifetime.

    Used as the FastAPI lifespan, so it runs once at startup and once at shutdown.

    Args:
        location: Project whose settings and database are opened.
        application: The app being started; routes read ``application.state``.

    Yields:
        Control while the app serves requests; the engine is disposed on shutdown.

    Raises:
        ConfigurationError: Settings or the database URL are invalid; startup fails.
        StorageError: The database cannot be opened.
    """
    settings = load_settings(location)
    configured = settings.database_url.get_secret_value() if settings.database_url else None
    async with open_database(build_database_url(location.state_dir, configured)) as engine:
        application.state.location = location
        application.state.settings = settings
        application.state.engine = engine
        yield


# Module-level so ``uvicorn app.main:app`` finds it; tests call create_app with a temp project.
app = create_app(ProjectLocation(root=DEFAULT_PROJECT_ROOT))

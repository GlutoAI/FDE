"""Report application and database status without calling any model."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncEngine

from app.database import get_engine, is_database_reachable
from app.llm.contracts import Contract

router = APIRouter()


class HealthResponse(Contract):
    """Application and database status; ``detail`` is a safe code, never an exception text."""

    status: Literal["ok", "error"] = Field(description="Overall status")
    db: Literal["connected", "disconnected"] = Field(description="Database reachability")
    detail: str | None = Field(default=None, description="Safe failure code when not ok")


@router.get(
    "/health",
    response_model=HealthResponse,
    response_model_exclude_none=True,
    responses={503: {"model": HealthResponse}},
)
async def check_health(
    response: Response, engine: Annotated[AsyncEngine, Depends(get_engine)]
) -> HealthResponse:
    """Return ok when the database answers, otherwise 503 with a safe code.

    Args:
        response: Outgoing response, whose status is set to 503 on failure.
        engine: Shared database engine.

    Returns:
        The application and database status.
    """
    if await is_database_reachable(engine):
        return HealthResponse(status="ok", db="connected")
    response.status_code = 503
    return HealthResponse(status="error", db="disconnected", detail="database_unavailable")

"""Run the connection agent through the fixture model; no HTTP route makes a paid request."""

from fastapi import APIRouter, HTTPException, Request

from app.agents.connection.models import ConnectionInput, ConnectionOutput
from app.bootstrap import create_connection_agent
from app.core.errors import AppError
from app.core.settings import ProjectLocation, Settings
from app.llm.contracts import AgentResult

router = APIRouter(prefix="/diagnostics")


@router.post("/connection", response_model=AgentResult[ConnectionOutput])
async def run_connection_check(request: Request) -> AgentResult[ConnectionOutput]:
    """Run one fixture connection probe, whatever model mode the settings select.

    Args:
        request: Current request, whose application state holds the location and settings.

    Returns:
        The validated probe output and its provenance.

    Raises:
        HTTPException: 502 with the safe error code when the agent fails.
    """
    location: ProjectLocation = request.app.state.location
    settings: Settings = request.app.state.settings
    fixture_settings = settings.model_copy(update={"model_mode": "fixture"})
    try:
        async with create_connection_agent(location, fixture_settings) as agent:
            return await agent.run_agent(ConnectionInput())
    except AppError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

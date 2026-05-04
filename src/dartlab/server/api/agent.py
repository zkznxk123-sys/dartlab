"""DartLab Agent Gateway API."""

from __future__ import annotations

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from ..agent_gateway import stream_agent_run
from ..models import AgentRunRequest

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/runs")
async def agent_runs(req: AgentRunRequest):
    """Run the DartLab research agent through the public AG-UI event stream."""
    return EventSourceResponse(stream_agent_run(req), media_type="text/event-stream")

"""DartLab Agent Gateway API."""

from __future__ import annotations

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from ..agentGateway import streamAgentRun
from ..models import AgentRunRequest

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/runs")
async def agentRuns(req: AgentRunRequest):
    """Run the DartLab research agent through the public AG-UI event stream."""
    return EventSourceResponse(streamAgentRun(req), media_type="text/event-stream")

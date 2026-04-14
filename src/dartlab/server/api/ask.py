"""LLM 질문 엔드포인트 — api_ask, plain_chat."""

from __future__ import annotations

import dartlab
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from ..models import AskRequest
from ..services.ai_analysis import run_plain_chat
from ..streaming import stream_ask

router = APIRouter()


@router.post("/api/ask")
async def api_ask(req: AskRequest):
    """LLM 질문 — AI가 질문 의도를 자율 판단하고 종목/매크로/비교를 결정한다."""
    dartlab.verbose = False

    if req.stream:
        return EventSourceResponse(
            stream_ask(req),
            media_type="text/event-stream",
        )

    return await run_plain_chat(req)

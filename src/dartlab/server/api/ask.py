"""LLM 질문 엔드포인트 — api_ask, plain_chat."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse

import dartlab
from dartlab.ai.runtime.artifacts import artifactPath

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


@router.get("/api/ask/artifacts/{day}/{filename}")
async def download_ask_artifact(day: str, filename: str):
    """AI tool_result 에서 생성된 CSV/JSON 아티팩트를 내려준다."""
    path = artifactPath(day, filename)
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="artifact not found")
    media_type = "application/json; charset=utf-8" if filename.endswith(".json") else "text/csv; charset=utf-8"
    return FileResponse(path, media_type=media_type, filename=filename)

"""LLM 질문 엔드포인트 — api_ask, plain_chat."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse

import dartlab
from dartlab import config as dartlab_config

from ..agent_gateway import stream_agent_run
from ..models import AgentRunMessage, AgentRunRequest, AskRequest
from ..services.ai_analysis import run_plain_chat

router = APIRouter()


@router.post("/api/ask")
async def api_ask(req: AskRequest):
    """LLM 질문 — AI가 질문 의도를 자율 판단하고 종목/매크로/비교를 결정한다."""
    dartlab.verbose = False

    if req.stream:
        return EventSourceResponse(
            _streamPublicAsk(req),
            media_type="text/event-stream",
        )

    return await run_plain_chat(req)


async def _streamPublicAsk(req: AskRequest):
    context = {}
    if req.company:
        context["company"] = {"stockCode": req.company, "company": req.company}
    elif req.viewContext and req.viewContext.company:
        company = req.viewContext.company
        context["company"] = {
            "stockCode": company.stockCode,
            "corpName": company.corpName,
            "company": company.company,
        }
    agent_req = AgentRunRequest(
        messages=[AgentRunMessage(role="user", content=req.question)],
        provider=req.provider,
        role=req.role,
        model=req.model,
        workspaceContext=context,
        stream=True,
    )
    async for event in stream_agent_run(agent_req):
        yield event


@router.get("/api/ask/artifacts/{day}/{filename}")
async def download_ask_artifact(day: str, filename: str):
    """AI tool_result 에서 생성된 CSV/JSON/JSONL 아티팩트를 내려준다."""
    path = _artifactPath(day, filename)
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="artifact not found")
    if filename.endswith(".jsonl"):
        media_type = "application/x-ndjson; charset=utf-8"
    elif filename.endswith(".json"):
        media_type = "application/json; charset=utf-8"
    else:
        media_type = "text/csv; charset=utf-8"
    return FileResponse(path, media_type=media_type, filename=filename)


def _artifactPath(day: str, filename: str) -> Path | None:
    normalized_day = day.replace("-", "")
    if not normalized_day.isdigit() or len(normalized_day) != 8:
        return None
    if Path(filename).name != filename:
        return None
    roots = [
        Path.home() / ".dartlab" / "ask_artifacts",
        Path(dartlab_config.dataDir) / "ai-artifacts",
    ]
    day_candidates = [normalized_day, day]
    for root in roots:
        for day_part in day_candidates:
            path = (root / day_part / filename).resolve()
            try:
                path.relative_to(root.resolve())
            except ValueError:
                continue
            if path.exists():
                return path
    return (roots[0] / normalized_day / filename).resolve()

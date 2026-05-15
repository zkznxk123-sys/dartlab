"""Master API dispatch — dartlab capability registry 의 HTTP face.

기존 EngineCall 도구 (src/dartlab/ai/tools/engineCall.py) 의 reflection-based
dispatch 로직을 HTTP 로 노출. capability registry (_generated.py) 화이트리스트로
보안. ui/web dashboard 의 모든 data fetch 가 본 엔드포인트를 통과해 dartlab
코드 변경 시 자동 따라감.

엔드포인트:
    POST /api/dl/call          — capability 호출
    GET  /api/dl/capabilities  — 전체 catalogue

Sig:
    POST /api/dl/call {apiRef, target?, args?, kwargs?}

Args:
    apiRef: str — "Company.show" / "Company.analysis" / "macro.rates" 등
    target: str | None — stockCode 등 1차 식별자
    args: list — positional args (보통 비움)
    kwargs: dict — keyword args (topic / axis / period / ...)

Returns:
    {ok, apiRef, target, message, data, refs}

Example:
    POST /api/dl/call
    {"apiRef": "Company.show", "target": "035720", "kwargs": {"topic": "is"}}

Raises:
    HTTPException(400) — apiRef 없음 / private API / registry 부재
    HTTPException(500) — capability 실행 내부 오류
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from dartlab.ai.tools.engineCall import engineCall
from dartlab.reference.capability._generated import CAPABILITIES

router = APIRouter(prefix="/api/dl", tags=["dl"])


class DlCallRequest(BaseModel):
    """Master dispatch payload — apiRef 기반 capability 호출."""

    apiRef: str = Field(..., description="public capability reference (e.g. 'Company.show')")
    target: str | None = Field(None, description="primary identifier (e.g. stockCode '035720')")
    args: list[Any] = Field(default_factory=list)
    kwargs: dict[str, Any] = Field(default_factory=dict)


@router.post("/call")
async def apiDlCall(req: DlCallRequest) -> dict[str, Any]:
    """Capability dispatch — EngineCall 의 HTTP face."""
    plan = {
        "apiRef": req.apiRef,
        "target": req.target or "",
        "args": req.args,
        "kwargs": req.kwargs,
    }
    result = engineCall(plan=plan)

    if not result.ok:
        code = result.error or ""
        bad_request_codes = {
            "missing_api_ref",
            "unknown_api_ref",
            "private_api_blocked",
            "unsupported_api_ref",
            "company_not_resolved",
            "not_callable",
        }
        status = 400 if code in bad_request_codes else 500
        raise HTTPException(
            status_code=status,
            detail={"error": code or "internal", "message": result.summary},
        )

    return {
        "ok": True,
        "apiRef": req.apiRef,
        "target": req.target,
        "message": result.summary,
        "data": result.data,
        "refs": [ref.toDict() for ref in result.refs],
    }


@router.get("/capabilities")
async def apiDlCapabilities() -> dict[str, Any]:
    """Capability catalogue — registry 의 모든 public capability 명단."""
    items = []
    for ref, meta in CAPABILITIES.items():
        items.append(
            {
                "apiRef": ref,
                "kind": meta.get("kind", "method") if isinstance(meta, dict) else "method",
                "summary": meta.get("summary", "") if isinstance(meta, dict) else "",
            }
        )
    return {"count": len(items), "items": items}

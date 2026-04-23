"""SSE 스트리밍 generator — core.runAsk() 이벤트 → SSE 변환.

[최우선 UX 원칙] 데이터 투명성 — 절대 제거 금지

모든 분석 로직은 engines/ai/core.py가 처리.
이 모듈은 이벤트를 SSE dict로 변환하는 thin adapter.

이벤트 흐름:
  meta          → 회사, 종목코드, 포함 모듈, 연도 범위
  snapshot      → 핵심 수치 (주가, 시총, PER 등)
  context       → 모듈별 데이터 (IS, BS, CF, ratios, dividend 등)
  system_prompt → 시스템 프롬프트 + LLM에 전달되는 전체 user content
  tool_call     → 에이전트 도구 호출
  tool_result   → 도구 실행 결과
  chart         → 차트 스펙
  ui_action     → canonical UI action
  chunk         → LLM 응답 텍스트 (실시간 스트리밍)
  validation    → 숫자 검증 결과
  done          → 완료 (responseMeta 포함)
  error         → 에러 + 사용자 행동 힌트
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass

from .models import AskRequest


@dataclass
class AnalysisStreamError(RuntimeError):
    """core.runAsk() error event surfaced to server adapters."""

    message: str
    action: str = ""
    detail: str | None = None


async def stream_ask(req: AskRequest):
    """core.runAsk() 이벤트 → SSE 변환.

    모든 분석 로직은 core.runAsk() 에 위임. 종목 resolve 는 AI 가 자율 판단.
    """
    kwargs = _build_kwargs(req)
    async for item in stream_analysis(req.question, **kwargs):
        yield item


async def stream_analysis(question: str = "", **kwargs):
    """core.runAsk() → SSE adapter."""
    from dartlab.ai.runtime.core import runAsk

    async for event in _sync_gen_to_async(runAsk, question, **kwargs):
        yield _sse(event.kind, event.data)


async def collect_analysis_text(question: str = "", **kwargs) -> str:
    """core.runAsk() 실행 후 chunk 텍스트 수집 (non-stream HTTP endpoint 용)."""
    from dartlab.ai.runtime.core import runAsk

    chunks: list[str] = []
    async for event in _sync_gen_to_async(runAsk, question, **kwargs):
        if event.kind == "chunk":
            chunks.append(event.data.get("text", ""))
        elif event.kind == "error":
            raise AnalysisStreamError(
                event.data.get("error", "analysis error"),
                action=event.data.get("action", ""),
                detail=event.data.get("detail"),
            )
    return "".join(chunks)


def _build_kwargs(req: AskRequest) -> dict:
    """AskRequest → core.runAsk() kwargs 변환."""
    kwargs: dict = {
        "provider": req.provider,
        "role": req.role,
        "model": req.model,
        "api_key": req.api_key,
        "base_url": req.base_url,
        "include": req.include,
        "exclude": req.exclude,
        "history": [h.model_dump() for h in req.history] if req.history else None,
        "view_context": req.viewContext.model_dump() if req.viewContext else None,
        "report_mode": req.reportMode,
    }

    # req.company / viewContext 종목코드 → AI stockCode 힌트로 전달
    hintCode = req.company
    if not hintCode and req.viewContext and req.viewContext.company:
        vc = req.viewContext.company
        hintCode = vc.stockCode or vc.corpName or vc.company
    if hintCode:
        kwargs["stockCode"] = hintCode

    return kwargs


def _sse(event: str, data: dict) -> dict:
    """이벤트 → SSE dict 변환."""
    return {"event": event, "data": json.dumps(data, ensure_ascii=False)}


async def _sync_gen_to_async(gen_fn, *args, **kwargs):
    """동기 제너레이터 → async 큐 브릿지.

    요청 scope 로 `pl.StringCache()` 컨텍스트를 감싼다. Polars 공식 권장
    패턴 — 전역 enable/disable 왕복 대신 요청 수명 동안만 카테고리 캐시
    공유, 컨텍스트 종료 시 자동 flush → 장기 프로세스에서 누적되지 않는다.
    요청 종료 finally 에서 `gc.collect()` 를 추가 호출해 Python 참조가
    해제된 DataFrame 의 Rust 힙 회수를 촉발한다.
    """
    import polars as pl

    with pl.StringCache():
        import queue as _queue_mod

        sync_queue: _queue_mod.Queue = _queue_mod.Queue(maxsize=64)
        _SENTINEL = object()

        def _run():
            try:
                for item in gen_fn(*args, **kwargs):
                    sync_queue.put(item)
            except Exception as exc:  # noqa: BLE001
                sync_queue.put(exc)
            finally:
                sync_queue.put(_SENTINEL)

        loop = asyncio.get_event_loop()
        task = loop.run_in_executor(None, _run)

        try:
            while True:
                item = await asyncio.to_thread(sync_queue.get)
                if item is _SENTINEL:
                    break
                if isinstance(item, Exception):
                    raise item
                yield item

            await task
        finally:
            _releaseRuntimeHeap()


def _releaseRuntimeHeap() -> None:
    """요청 종료 시 GC 촉발. StringCache 는 컨텍스트가 담당하므로 생략."""
    try:
        import gc

        gc.collect()
    except Exception:  # noqa: BLE001
        pass

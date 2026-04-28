"""SSE 스트리밍 generator — core.runAsk() 이벤트 → SSE 변환.

[최우선 UX 원칙] 데이터 투명성 — 절대 제거 금지

모든 분석 로직은 dartlab.ai.runtime.core 가 처리.
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
  quality_check → AI 최종 응답 품질 계약 검사 결과
  done          → 완료 (responseMeta 포함)
  error         → 에러 + 사용자 행동 힌트
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
from dataclasses import dataclass

from dartlab.ai.runtime.audit import AuditCollector

from .models import AskRequest

log = logging.getLogger(__name__)

# Streaming 안정성 튜닝 (환경변수 override 가능)
#   DARTLAB_STREAM_QUEUE_MAX — async bridge 큐 최대 엔트리 (기본 1024).
#                              64 고정 시 chunk 폭주하면 producer blocking.
#   DARTLAB_STREAM_PUT_TIMEOUT — queue.put 타임아웃(초). 느린 소비자·disconnect 감지.
_DEFAULT_QUEUE_MAX = int(os.environ.get("DARTLAB_STREAM_QUEUE_MAX", "1024"))
_DEFAULT_PUT_TIMEOUT = float(os.environ.get("DARTLAB_STREAM_PUT_TIMEOUT", "30"))


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
    auditor = AuditCollector(
        question=req.question,
        stockCode_hint=kwargs.get("stockCode"),
        provider=kwargs.get("provider"),
        model=kwargs.get("model"),
    )
    try:
        async for item in stream_analysis(req.question, _audit=auditor, **kwargs):
            yield item
    finally:
        auditor.flush()


async def stream_analysis(question: str = "", *, _audit: AuditCollector | None = None, **kwargs):
    """core.runAsk() → SSE adapter."""
    from dartlab.ai.runtime.core import runAsk

    async for event in _sync_gen_to_async(runAsk, question, **kwargs):
        if _audit is not None:
            _audit.observe(event.kind, event.data)
        yield _sse(event.kind, event.data)


async def collect_analysis_text(question: str = "", **kwargs) -> str:
    """core.runAsk() 실행 후 chunk 텍스트 수집 (non-stream HTTP endpoint 용)."""
    from dartlab.ai.runtime.core import runAsk

    auditor = AuditCollector(
        question=question,
        stockCode_hint=kwargs.get("stockCode"),
        provider=kwargs.get("provider"),
        model=kwargs.get("model"),
    )
    chunks: list[str] = []
    try:
        async for event in _sync_gen_to_async(runAsk, question, **kwargs):
            auditor.observe(event.kind, event.data)
            if event.kind == "chunk":
                chunks.append(event.data.get("text", ""))
            elif event.kind == "error":
                raise AnalysisStreamError(
                    event.data.get("error", "analysis error"),
                    action=event.data.get("action", ""),
                    detail=event.data.get("detail"),
                )
    finally:
        auditor.flush()
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
    """동기 제너레이터 → async 큐 브릿지 (timeout · cancel 대응).

    요청 종료(정상·예외·소비자 break·asyncio cancel 모두) 시 Polars string cache 를
    해제하고 GC 를 촉발한다. `/api/ask` 요청마다 AI tool loop 가 만든
    Company 인스턴스·pivot DataFrame 이 쌓여 네이티브 힙이 비대화하는
    문제 방어 — `pl.disable_string_cache()` 는 100~200MB, `gc.collect()`
    는 Python 참조가 해제된 DataFrame 의 Rust 힙 회수를 촉발한다.
    BoundedCache 의 EMERGENCY 임계를 넘지 못한 중간 누적분을 요청 경계
    에서 정리하는 용도.

    안정성 튜닝:
      - queue maxsize : env `DARTLAB_STREAM_QUEUE_MAX` (기본 1024).
      - put timeout   : env `DARTLAB_STREAM_PUT_TIMEOUT` (기본 30초).
      - consumer cancel 시 `cancelled` Event 로 producer thread 조기 종료.
    """
    import queue as _queue_mod

    sync_queue: _queue_mod.Queue = _queue_mod.Queue(maxsize=_DEFAULT_QUEUE_MAX)
    cancelled = threading.Event()
    _SENTINEL = object()

    def _run():
        try:
            for item in gen_fn(*args, **kwargs):
                if cancelled.is_set():
                    break
                try:
                    sync_queue.put(item, timeout=_DEFAULT_PUT_TIMEOUT)
                except _queue_mod.Full:
                    log.warning(
                        "stream producer: queue put timeout (%.0fs) — slow consumer or disconnect",
                        _DEFAULT_PUT_TIMEOUT,
                    )
                    break
        except Exception as exc:  # noqa: BLE001
            try:
                sync_queue.put(exc, timeout=_DEFAULT_PUT_TIMEOUT)
            except _queue_mod.Full:
                pass
        finally:
            try:
                sync_queue.put(_SENTINEL, timeout=_DEFAULT_PUT_TIMEOUT)
            except _queue_mod.Full:
                pass

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
    except asyncio.CancelledError:
        # ASGI disconnect 또는 상위 task cancel — producer 조기 종료 신호
        cancelled.set()
        raise
    finally:
        _releaseRuntimeHeap()


def _releaseRuntimeHeap() -> None:
    """요청 종료 시 Polars 네이티브 힙 회수 촉발. 실패해도 조용히 넘어간다."""
    try:
        import polars as pl

        pl.disable_string_cache()
    except (ImportError, AttributeError):
        pass
    try:
        import gc

        gc.collect()
    except Exception:  # noqa: BLE001
        pass

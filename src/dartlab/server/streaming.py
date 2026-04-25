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
import logging
import os
import threading
from dataclasses import dataclass

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
    auditor = _AuditCollector(question=req.question)
    try:
        async for item in stream_analysis(req.question, _audit=auditor, **kwargs):
            yield item
    finally:
        auditor.flush()


async def stream_analysis(question: str = "", *, _audit: "_AuditCollector | None" = None, **kwargs):
    """core.runAsk() → SSE adapter."""
    from dartlab.ai.runtime.core import runAsk

    async for event in _sync_gen_to_async(runAsk, question, **kwargs):
        if _audit is not None:
            _audit.observe(event.kind, event.data)
        yield _sse(event.kind, event.data)


async def collect_analysis_text(question: str = "", **kwargs) -> str:
    """core.runAsk() 실행 후 chunk 텍스트 수집 (non-stream HTTP endpoint 용)."""
    from dartlab.ai.runtime.core import runAsk

    auditor = _AuditCollector(question=question)
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


# ── Audit 로그 수집 ──────────────────────────────────────────────
#
# 요청 단위로 tool_call · chunk · error 이벤트를 집계해 JSONL 한 줄로 기록한다.
# 위치: ``{dataDir}/audit/ai-ask/YYYY-MM-DD.jsonl``. Phase 1 선행 인프라 (ops/skills.md §5).
# 판정 (P/T/C/V) 은 후속 스크립트가 파일을 읽어 사람이 채움. 여기서는 원재료만.


@dataclass
class _AuditCollector:
    """요청 내 이벤트를 모아 종료 시 JSONL 한 줄로 flush.

    주의: 다중 요청 동시 처리 안전 — 각 요청이 자기 인스턴스 보유. 로컬 append 만.
    파일 I/O 실패는 조용히 삼킨다 (audit 기록 실패로 본 응답을 깨지 않음).
    """

    question: str
    tool_calls: list[dict] = None  # type: ignore[assignment]
    chunk_len: int = 0
    error: str | None = None
    skill_used: str | None = None

    def __post_init__(self) -> None:
        if self.tool_calls is None:
            self.tool_calls = []

    def observe(self, kind: str, data: dict) -> None:
        if kind == "tool_call":
            name = data.get("name") or data.get("tool") or ""
            args = data.get("args") or data.get("arguments") or {}
            self.tool_calls.append({"name": str(name), "args": args if isinstance(args, dict) else {}})
            # skill 사용 힌트 — pythonExec 안에서 SKILL.md 를 읽거나 skills 모듈 import 하면 기록
            if name == "pythonExec" and isinstance(args, dict):
                code = str(args.get("code", ""))
                if "src/dartlab/skills/" in code or "from dartlab.skills" in code:
                    # 간단 휴리스틱 — skill 이름 추출
                    import re

                    m = re.search(r"skills/([a-z0-9-]+)/", code)
                    if m:
                        self.skill_used = m.group(1)
        elif kind == "chunk":
            self.chunk_len += len(str(data.get("text", "")))
        elif kind == "error":
            self.error = str(data.get("error") or "")

    def flush(self) -> None:
        try:
            import datetime as _dt
            import hashlib
            import uuid

            from dartlab.core.dataLoader import _getDataRoot

            root = _getDataRoot() / "audit" / "ai-ask"
            root.mkdir(parents=True, exist_ok=True)
            day = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")
            path = root / f"{day}.jsonl"

            # v2 스키마 필드 계산
            def _sha16(text: str) -> str:
                return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

            # tool_sequence_hash
            seq_src = ",".join(
                f"{tc.get('name', '')}:{_sha16(json.dumps(tc.get('args', {}), sort_keys=True, default=str, ensure_ascii=False))}"
                for tc in self.tool_calls
            )
            tool_sequence_hash = "seq:" + hashlib.sha256(seq_src.encode("utf-8")).hexdigest()[:16]

            # question_hash (정규화 후)
            import re as _re

            q_norm = _re.sub(r"\s+", " ", _re.sub(r"[^\w\s가-힣]", "", self.question.lower().strip()))
            question_hash = _sha16(q_norm) if self.question else ""

            entry = {
                "schema_version": 2,
                "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(),
                "request_id": f"req-{uuid.uuid4().hex[:12]}",
                "question": self.question,
                "question_hash": question_hash,
                "category_hash": "",
                "stockCode_hint": None,
                "provider": None,
                "model": None,
                "tool_calls": self.tool_calls,
                "tool_sequence_hash": tool_sequence_hash,
                "override_calls": [],
                "rounds": max(1, len(self.tool_calls)),
                "chunk_len": self.chunk_len,
                "error": self.error,
                "violation": None,
                "skill_used": self.skill_used,
                "duration_total_ms": None,
                "judgment": {"verdict": None, "judged_at": None, "judged_by": None, "pr_url": None},
            }
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except (OSError, ValueError, TypeError, ImportError):
            # audit 실패로 응답 경로 깨지지 않음
            pass


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

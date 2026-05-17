"""Constrained Python execution tool for DartLab analysis.

안전 장치:
- 실행 시간 한도: env DARTLAB_RUNPYTHON_TIMEOUT_SEC (기본 60). 별 thread 에서 실행하고
  한도 초과면 결과 무시 (interpreter 강제 중단은 하지 않으므로 background 누수는 가능).
- emit_result 누락 안내: emitted 가 비면 GATE 가 차단할 것이라는 hint 메시지.
"""

from __future__ import annotations

import json
import logging
import os
import re
import textwrap
import threading
import time
import traceback
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from typing import Any

from dartlab.ai.contracts import Ref

from .formatting import shortText
from .runpythonGuard import _assertSafeAst, _safeOpenFactory
from .types import ToolResult

logger = logging.getLogger(__name__)

_TIMEOUT_SEC = float(os.environ.get("DARTLAB_RUNPYTHON_TIMEOUT_SEC", "60"))


_BLOCK_KEYWORDS = (
    "def ",
    "class ",
    "for ",
    "while ",
    "if ",
    "elif ",
    "else:",
    "try:",
    "except",
    "finally:",
    "with ",
)


def _tryUnindentFallback(code: str) -> str | None:
    """단일 statement series 코드면 모든 줄 lstrip — IndentationError 자동 복구.

    블록 키워드 (def/for/if/...) 가 있으면 들여쓰기가 *의미 있다* — 안전상 None.
    LLM 이 1 줄만 잘못 indent 한 경우 (사용자가 본 ` df = dartlab.scan(...)`) 정상화.
    """
    if any(kw in code for kw in _BLOCK_KEYWORDS):
        return None
    stripped = "\n".join(line.lstrip() for line in code.split("\n"))
    if stripped == code:
        return None  # 변화 없음 — 다시 try 의미 X.
    return stripped


def _lastTracebackLine(tracebackText: str) -> str:
    """traceback 마지막 비어있지 않은 줄 (보통 `ExceptionName: message`) 반환.

    UI 답변 헤더·summary 에 한 줄 진단 노출용. 추출 실패 시 빈 문자열.
    """
    text = (tracebackText or "").strip()
    if not text:
        return ""
    for line in reversed(text.splitlines()):
        s = line.strip()
        if not s:
            continue
        # 너무 길면 자름 — UI summary 한 줄 가독성.
        return s[:240]
    return ""


def _diagnoseErrorHint(tracebackText: str) -> str:
    """LLM 코드 결함 분류 — 자주 보이는 polars / pandas / dartlab API 패턴.

    LLM 다음 turn 에 같은 실수 안 하게 *짧은 한국어 hint* 반환. 매칭 안 되면 빈 문자열.
    """
    text = tracebackText or ""
    # polars projection 시 같은 출력 컬럼명 두 번 — agent 가 alias 강제 rename 시 자주.
    if "duplicate output name" in text or "DuplicateError" in text:
        return (
            "동일 컬럼명을 select 안에서 두 번 사용 — scan/show 결과 컬럼은 rename 없이 그대로 select. "
            "alias 가 필요하면 *기존 이름과 다른* 이름만 부여."
        )
    # 컬럼 미존재 — agent 가 추측한 컬럼명이 실제 결과와 불일치.
    if "ColumnNotFound" in text or "not found" in text.lower():
        return "컬럼명 불일치 — df.columns 로 실제 이름 먼저 확인 후 select."
    # IndentationError — leading space (이미 dedent 시도하지만 mixed indent 는 못 잡음).
    if "IndentationError" in text or "TabError" in text:
        return "코드 들여쓰기 결함 — 모든 라인을 0 indent 에서 시작 (def/for/if 본체만 4-space 들여쓰기)."
    # SyntaxError — 일반.
    if "SyntaxError" in text:
        return "Python 구문 오류 — 코드 수정 후 재시도."
    # NameError — 미정의 변수 (보통 import 누락).
    if "NameError" in text:
        return "정의되지 않은 이름 — import 또는 사전 변수 선언 누락. 사용 가능: dartlab, pl, normalizeColumn, columnsFor, availableTopics."
    # AttributeError on dartlab — 잘못된 API 이름.
    if "AttributeError" in text and "dartlab" in text:
        return "dartlab 모듈에 없는 속성 호출 — ReadCapability 로 정확한 API 이름 확인."
    return ""


def runPython(code: str, *, runId: str | None = None) -> ToolResult:
    """sandboxed Python 실행 — stdout/stderr 캡처 + emit_result 결과 수집."""
    stdout = StringIO()
    stderr = StringIO()
    emitted: dict[str, Any] = {}

    def _coerceValue(value: Any) -> Any:
        """JSON 가능한 형태로 재귀 변환. polars DataFrame/Series, dict, list 안까지 walk."""
        try:
            import polars as _pl

            if isinstance(value, _pl.DataFrame):
                return [{k: _coerceValue(v) for k, v in row.items()} for row in value.to_dicts()]
            if isinstance(value, _pl.Series):
                return [_coerceValue(v) for v in value.to_list()]
        except ImportError:
            pass
        if isinstance(value, dict):
            return {k: _coerceValue(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [_coerceValue(v) for v in value]
        return value

    def emitResult(*args: Any, **kwargs: Any) -> None:
        """Result emitter — keyword args 권장. positional dict 도 dict 로 unpack 해서 받음."""
        payload: dict[str, Any] = {}
        for arg in args:
            arg = _coerceValue(arg)
            if isinstance(arg, dict):
                payload.update(arg)
            else:
                payload.setdefault("values", {})
                if isinstance(payload["values"], dict):
                    payload["values"][f"value_{len(payload['values'])}"] = arg
        for k, v in kwargs.items():
            payload[k] = _coerceValue(v)
        emitted.update(payload)
        print("DARTLAB_RESULT_JSON=" + json.dumps(payload, ensure_ascii=False, default=str))

    # sandbox guard — write 가능 mode 의 open 은 안전 경로 prefix 로 제한.
    # 차단 호출 (os.system / subprocess.run 등) 은 exec 직전 AST 검사로 거부.
    globals_dict: dict[str, Any] = {
        "emit_result": emitResult,
        "__builtins__": __builtins__,
        "open": _safeOpenFactory(),
    }
    container: dict[str, Any] = {}

    def _runner() -> None:
        try:
            import polars as pl

            import dartlab
            from dartlab.ai.tools.columnAlias import (
                availableTopics,
                columnsFor,
                normalizeColumn,
            )

            globals_dict.update(
                {
                    "dartlab": dartlab,
                    "pl": pl,
                    # 컬럼 정규화 헬퍼 — 한국어 / snake / alias → 표준 snake_id.
                    "normalizeColumn": normalizeColumn,
                    "columnsFor": columnsFor,
                    "availableTopics": availableTopics,
                }
            )
            # textwrap.dedent — *공통* leading whitespace 만 제거. mixed-indent
            # (한 줄만 indent 된 LLM 결함) 는 못 잡음 → IndentationError fallback 으로
            # 처리: 블록 키워드 없으면 모든 줄 lstrip 해서 재시도.
            normalized_code = textwrap.dedent(str(code or "")).strip()
            # AST sandbox guard — destructive shell/import 호출 거부.
            _assertSafeAst(normalized_code)
            with redirect_stdout(stdout), redirect_stderr(stderr):
                try:
                    exec(normalized_code, globals_dict, globals_dict)  # noqa: S102
                except IndentationError:
                    fallback = _tryUnindentFallback(normalized_code)
                    if fallback is None:
                        raise
                    _assertSafeAst(fallback)
                    exec(fallback, globals_dict, globals_dict)  # noqa: S102
        except Exception:  # noqa: BLE001
            container["error"] = traceback.format_exc()

    start = time.monotonic()
    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join(timeout=_TIMEOUT_SEC)
    if thread.is_alive():
        duration = int((time.monotonic() - start) * 1000)
        return ToolResult(
            False,
            f"run_python timeout ({_TIMEOUT_SEC:.0f}s)",
            refs=[
                Ref(
                    id=f"execution:{runId or 'local'}:timeout",
                    kind="executionRef",
                    title="python execution timeout",
                    source="run_python",
                    payload={"durationMs": duration, "timeoutSec": _TIMEOUT_SEC},
                )
            ],
            data={"stdout": stdout.getvalue(), "stderr": stderr.getvalue(), "durationMs": duration},
            error="python_execution_timeout",
        )
    if "error" in container:
        duration = int((time.monotonic() - start) * 1000)
        logger.warning(
            "run_python failed (runId=%s, %dms)\n--- code ---\n%s\n--- traceback ---\n%s",
            runId or "local",
            duration,
            (code or "")[:1500],
            container["error"],
        )
        # 흔한 모델 코드 결함 → 다음 turn 에 같은 실수 안 하게 hint 부착.
        # 단순 substring 매칭 — 정밀도보다 다음 attempt 의 가이드성 우선.
        traceback_text = container["error"]
        hint = _diagnoseErrorHint(traceback_text)
        errorLine = _lastTracebackLine(traceback_text)
        summary = "run_python 실행 실패"
        if errorLine:
            summary = f"run_python 실행 실패 — {errorLine}"
        elif hint:
            summary = f"run_python 실행 실패 — {hint}"
        return ToolResult(
            False,
            summary,
            refs=[
                Ref(
                    id=f"execution:{runId or 'local'}:failed",
                    kind="executionRef",
                    title="python execution failed",
                    source="run_python",
                    payload={
                        "durationMs": duration,
                        "stderr": traceback_text,
                        "hint": hint,
                        "errorLine": errorLine,
                    },
                )
            ],
            data={
                "stdout": stdout.getvalue(),
                "stderr": stderr.getvalue(),
                # 실제 exception traceback — UI 가 errorBody 로 펼침. data.stderr (스트림 캡처)
                # 은 raise 시 비어있어서 user 가 진단 못 함 → 별도 필드 노출.
                "traceback": traceback_text,
                "errorLine": errorLine,
                "durationMs": duration,
                "hint": hint,
            },
            error="python_execution_failed",
        )
    duration = int((time.monotonic() - start) * 1000)
    refs = [
        Ref(
            id=f"execution:{runId or 'local'}:{duration}",
            kind="executionRef",
            title="python execution",
            source="run_python",
            payload={
                "durationMs": duration,
                "stdout": shortText(stdout.getvalue(), limit=4000),
                "stderr": shortText(stderr.getvalue(), limit=4000),
                "result": emitted,
            },
        )
    ]
    table_value = emitted.get("table")
    if table_value is not None and (not hasattr(table_value, "__len__") or len(table_value) > 0):
        refs.append(
            Ref(
                id=f"table:{runId or 'local'}:python",
                kind="tableRef",
                title="python table result",
                source=refs[0].id,
                payload={"rows": table_value},
            )
        )
    values_raw = emitted.get("values")
    if isinstance(values_raw, dict) and values_raw:
        values = values_raw
        for key, value in values.items():
            refs.append(
                Ref(
                    id=f"value:{runId or 'local'}:{key}",
                    kind="valueRef",
                    title=str(key),
                    source=refs[0].id,
                    payload={"key": key, "value": value, "unit": (emitted.get("units") or {}).get(key)},
                )
            )
    date_value = emitted.get("date") or emitted.get("dateRef")
    if date_value:
        refs.append(
            Ref(
                id=f"date:{runId or 'local'}:{str(date_value)[:32]}",
                kind="dateRef",
                title=str(date_value),
                source=refs[0].id,
                payload={"value": str(date_value)},
            )
        )
    sources_raw = emitted.get("sources") or emitted.get("sourceRefs")
    if isinstance(sources_raw, dict):
        sources_iter = [sources_raw]
    elif isinstance(sources_raw, list):
        sources_iter = [item for item in sources_raw if isinstance(item, dict)]
    else:
        sources_iter = []
    for idx, source_payload in enumerate(sources_iter):
        source_id = str(source_payload.get("id") or f"source_{idx}")
        safe_id = re.sub(r"[^A-Za-z0-9_.:-]+", "_", source_id)[:96]
        refs.append(
            Ref(
                id=f"source:{runId or 'local'}:{safe_id}",
                kind="sourceRef",
                title=str(source_payload.get("title") or source_id),
                source=source_payload.get("url") or refs[0].id,
                payload=source_payload,
            )
        )
    summary = "run_python 실행 완료"
    if not emitted:
        summary += " (emit_result 호출 없음 — GATE 가 차단할 가능성)"
    return ToolResult(
        True,
        summary,
        refs=refs,
        data={"stdout": stdout.getvalue(), "stderr": stderr.getvalue(), "result": emitted, "durationMs": duration},
    )

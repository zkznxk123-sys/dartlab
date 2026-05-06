"""Constrained Python execution tool for DartLab analysis.

안전 장치:
- 실행 시간 한도: env DARTLAB_RUNPYTHON_TIMEOUT_SEC (기본 60). 별 thread 에서 실행하고
  한도 초과면 결과 무시 (interpreter 강제 중단은 하지 않으므로 background 누수는 가능).
- emit_result 누락 안내: emitted 가 비면 GATE 가 차단할 것이라는 hint 메시지.
"""

from __future__ import annotations

import json
import os
import threading
import time
import traceback
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from typing import Any

from dartlab.ai.contracts import Ref

from .formatting import short_text
from .types import ToolResult

_TIMEOUT_SEC = float(os.environ.get("DARTLAB_RUNPYTHON_TIMEOUT_SEC", "60"))


def runPython(code: str, *, runId: str | None = None) -> ToolResult:
    stdout = StringIO()
    stderr = StringIO()
    emitted: dict[str, Any] = {}

    def emit_result(**kwargs: Any) -> None:
        emitted.update(kwargs)
        print("DARTLAB_RESULT_JSON=" + json.dumps(kwargs, ensure_ascii=False, default=str))

    globals_dict: dict[str, Any] = {"emit_result": emit_result, "__builtins__": __builtins__}
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
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exec(str(code or ""), globals_dict, globals_dict)  # noqa: S102
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
        return ToolResult(
            False,
            "run_python 실행 실패",
            refs=[
                Ref(
                    id=f"execution:{runId or 'local'}:failed",
                    kind="executionRef",
                    title="python execution failed",
                    source="run_python",
                    payload={"durationMs": duration, "stderr": container["error"]},
                )
            ],
            data={"stdout": stdout.getvalue(), "stderr": stderr.getvalue(), "durationMs": duration},
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
                "stdout": short_text(stdout.getvalue(), limit=4000),
                "stderr": short_text(stderr.getvalue(), limit=4000),
                "result": emitted,
            },
        )
    ]
    if emitted.get("table"):
        refs.append(
            Ref(
                id=f"table:{runId or 'local'}:python",
                kind="tableRef",
                title="python table result",
                source=refs[0].id,
                payload={"rows": emitted.get("table")},
            )
        )
    if emitted.get("values"):
        values = emitted.get("values") if isinstance(emitted.get("values"), dict) else {}
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
    summary = "run_python 실행 완료"
    if not emitted:
        summary += " (emit_result 호출 없음 — GATE 가 차단할 가능성)"
    return ToolResult(
        True,
        summary,
        refs=refs,
        data={"stdout": stdout.getvalue(), "stderr": stderr.getvalue(), "result": emitted, "durationMs": duration},
    )

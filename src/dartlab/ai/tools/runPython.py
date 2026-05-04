"""Constrained Python execution tool for DartLab analysis."""

from __future__ import annotations

import json
import time
import traceback
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from typing import Any

from dartlab.ai.contracts import Ref

from .formatting import short_text
from .types import ToolResult


def runPython(code: str, *, runId: str | None = None) -> ToolResult:
    stdout = StringIO()
    stderr = StringIO()
    emitted: dict[str, Any] = {}

    def emit_result(**kwargs: Any) -> None:
        emitted.update(kwargs)
        print("DARTLAB_RESULT_JSON=" + json.dumps(kwargs, ensure_ascii=False, default=str))

    globals_dict: dict[str, Any] = {"emit_result": emit_result, "__builtins__": __builtins__}
    start = time.monotonic()
    try:
        import polars as pl

        import dartlab

        globals_dict.update({"dartlab": dartlab, "pl": pl})
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exec(str(code or ""), globals_dict, globals_dict)  # noqa: S102
    except Exception:  # noqa: BLE001
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
                    payload={"durationMs": duration, "stderr": traceback.format_exc()},
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
    return ToolResult(
        True,
        "run_python 실행 완료",
        refs=refs,
        data={"stdout": stdout.getvalue(), "stderr": stderr.getvalue(), "result": emitted, "durationMs": duration},
    )

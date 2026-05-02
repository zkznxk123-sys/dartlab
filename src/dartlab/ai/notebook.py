"""Bounded Python execution for Ask Workbench."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .contracts import Ref, new_id
from .datasets import RuntimeDatasetCatalog

_STDOUT_CAP = 60_000
_STDERR_CAP = 20_000
_RESERVED_HELPER_RE = re.compile(r"(?m)^\s*(def\s+emit_result\b|emit_result\s*=)")


@dataclass(frozen=True)
class ExecutionResult:
    ok: bool
    code: str
    returncode: int | None
    stdout: str
    stderr: str
    duration_ms: int
    timeout: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_python(code: str, *, timeout: int = 60, cwd: str | None = None) -> ExecutionResult:
    """Python 실행 — DartLab 라이브러리를 코드로 조합하는 핵심 action.

    Description
    -----------
    LLM 이 작성한 Python 코드를 제한된 subprocess 에서 실행하고 stdout/stderr,
    return code, duration 을 ExecutionResult 로 반환한다. DartLab import 와
    runtime dataset root 를 사용할 수 있도록 실행 환경을 구성한다.

    Parameters
    ----------
    code : str
        실행할 Python 코드.
    timeout : int, optional
        최대 실행 시간 (초). 1~120초 범위로 제한된다.
    cwd : str, optional
        실행 작업 디렉터리. None 이면 repo root 를 사용한다.

    Returns
    -------
    ExecutionResult
        ok : bool — returncode 0 여부
        code : str — 실행한 코드
        returncode : int | None — 프로세스 종료 코드
        stdout : str — 표준 출력
        stderr : str — 표준 에러
        duration_ms : int — 실행 시간 (ms)
        timeout : bool — timeout 발생 여부

    Raises
    ------
    없음
        실행 실패와 timeout 은 ExecutionResult 로 반환한다.

    Examples
    --------
    >>> run_python('emit_result(values={"value": 1})').ok
    True

    Notes
    -----
    구조화 결과는 prelude 의 `emit_result()` helper 로 출력한다.

    Guide
    -----
    계산·랭킹·비교·시계열 질문은 DartLab API 를 이 action 안에서 직접 조합한다.

    See Also
    --------
    execution_to_ref : 실행 결과를 execution ref 로 변환.
    """

    import time

    timeout = max(1, min(int(timeout), 120))
    if _redefines_reserved_helper(code):
        return ExecutionResult(
            ok=False,
            code=code,
            returncode=2,
            stdout="",
            stderr="Do not define or assign emit_result; call the workbench-provided emit_result(...) helper.",
            duration_ms=0,
        )
    workdir = Path(cwd or _repo_root())
    env = _execution_env(workdir)
    start = time.monotonic()
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".py", delete=False) as handle:
        path = Path(handle.name)
        handle.write(_script_prelude(workdir))
        handle.write("\n")
        handle.write(code)
    try:
        proc = subprocess.run(
            [sys.executable, "-X", "utf8", str(path)],
            cwd=str(workdir),
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        duration_ms = int((time.monotonic() - start) * 1000)
        return ExecutionResult(
            ok=proc.returncode == 0,
            code=code,
            returncode=proc.returncode,
            stdout=_cap(proc.stdout, _STDOUT_CAP),
            stderr=_cap(proc.stderr, _STDERR_CAP),
            duration_ms=duration_ms,
        )
    except subprocess.TimeoutExpired as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        return ExecutionResult(
            ok=False,
            code=code,
            returncode=None,
            stdout=_cap(str(exc.stdout or ""), _STDOUT_CAP),
            stderr=_cap(str(exc.stderr or "") + f"\nExecution timed out after {timeout}s", _STDERR_CAP),
            duration_ms=duration_ms,
            timeout=True,
        )
    finally:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def execution_to_ref(result: ExecutionResult) -> Ref:
    return Ref(id=new_id("execution"), kind="execution", source="run_python", payload=result.to_dict())


runPython = run_python


def _redefines_reserved_helper(code: str) -> bool:
    return bool(_RESERVED_HELPER_RE.search(code))


def _execution_env(workdir: Path) -> dict[str, str]:
    env = os.environ.copy()
    src = workdir / "src"
    current = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(src) + (os.pathsep + current if current else "")
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    catalog = RuntimeDatasetCatalog()
    if catalog.roots and "DARTLAB_DATA_DIR" not in env:
        env["DARTLAB_DATA_DIR"] = str(catalog.roots[0])
    return env


def _script_prelude(workdir: Path) -> str:
    return (
        "from pathlib import Path\n"
        "import json\n"
        "import polars as pl\n"
        f"WORKSPACE_ROOT = Path({str(workdir)!r})\n"
        "DATASET_ROOTS = [Path(p) for p in __import__('os').environ.get('DARTLAB_DATA_DIR', '').split(';') if p]\n"
        "\n"
        "def emit_result(rows=None, values=None, meta=None, limits=None, units=None, formulas=None, inputs=None, **extra):\n"
        "    if isinstance(rows, str) and isinstance(values, list):\n"
        "        meta = dict(meta or {})\n"
        "        meta.setdefault('label', rows)\n"
        "        rows, values = values, None\n"
        "    if isinstance(rows, dict):\n"
        "        named = [(k, v) for k, v in rows.items() if isinstance(v, list) and v and all(isinstance(r, dict) for r in v)]\n"
        "        if len(named) == 1:\n"
        "            meta = dict(meta or {})\n"
        "            meta.setdefault('label', named[0][0])\n"
        "            rows = named[0][1]\n"
        "    payload = {}\n"
        "    if rows is not None:\n"
        "        payload['rows'] = rows\n"
        "    if values is not None:\n"
        "        payload['values'] = values\n"
        "    if meta is not None:\n"
        "        payload['meta'] = meta\n"
        "    if limits is not None:\n"
        "        payload['limits'] = limits\n"
        "    if units is not None:\n"
        "        payload['units'] = units\n"
        "    if formulas is not None:\n"
        "        payload['formulas'] = formulas\n"
        "    if inputs is not None:\n"
        "        payload['inputs'] = inputs\n"
        "    payload.update(extra)\n"
        "    print('DARTLAB_RESULT_JSON=' + json.dumps(payload, ensure_ascii=False, default=str))\n"
    )


def _repo_root() -> Path:
    here = Path.cwd()
    for base in [here, *here.parents]:
        if (base / "pyproject.toml").exists() and (base / "src" / "dartlab").exists():
            return base
    return here


def _cap(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...[truncated {len(text) - limit} chars]"

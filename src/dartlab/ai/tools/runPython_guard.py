"""RunPython sandbox 최소 차단 + 경로 가드 (Option B).

dartlab 의 *단일 사용자 로컬 신뢰* stance 와 정합. 외부 클라이언트가 attach 한 상태에서
의도적/실수로 destructive 호출 시도해도 *명시적 거부 + 안내* 로 보호.

차단 대상:
- `os.system` / `os.popen` / `os.exec*` / `os.spawn*` / `os.kill` 호출
- `subprocess.run` / `Popen` / `call` / `check_call` / `check_output` / `getoutput` / `getstatusoutput`
- `shutil.rmtree` / `shutil.move`
- `socket.socket` (raw socket 생성)
- `__import__("os" | "subprocess" | "shutil" | "socket")` 우회
- `from os import system` 등 destructive 항목 직접 import
- `open(path, mode)` 의 path 가 안전 경로 외 + mode 가 write/append/exec → 차단

허용:
- `os.path.*`, `os.environ.*`, `os.getcwd()` 등 read-only os 사용 (호출 attr 만 차단)
- `pathlib.Path` 읽기
- 안전 경로 (~/.dartlab/, ./tmp/, /tmp/, $TEMP/) 안의 파일 쓰기
- import 자체는 허용 — 호출 시점에 차단
"""

from __future__ import annotations

import ast
import os
import os.path
import tempfile
from typing import Any, Callable

_BLOCKED_ATTR_CALLS: dict[str, set[str]] = {
    "os": {
        "system",
        "popen",
        "execv",
        "execve",
        "execvp",
        "execvpe",
        "spawnv",
        "spawnve",
        "spawnvp",
        "spawnvpe",
        "kill",
        "remove",
        "unlink",
        "rmdir",
        "removedirs",
    },
    "subprocess": {
        "run",
        "Popen",
        "call",
        "check_call",
        "check_output",
        "getoutput",
        "getstatusoutput",
    },
    "shutil": {"rmtree", "move", "copytree"},
    "socket": {"socket", "create_connection", "create_server"},
}

_BLOCKED_IMPORT_TARGETS: set[str] = set(_BLOCKED_ATTR_CALLS.keys())


def _assertSafeAst(code: str) -> None:
    """exec 직전 AST 검사. 차단 대상 발견 시 PermissionError raise.

    차단은 *호출 시점* 기준 — `import os` 자체는 허용, `os.system(...)` 호출 시점에 거부.
    덕분에 `os.path.expanduser` 같은 read-only 사용은 그대로 작동.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        # 정상 SyntaxError 는 exec 가 다시 raise 하도록 그대로 통과.
        return

    for node in ast.walk(tree):
        # ① os.system(...) / subprocess.run(...) / shutil.rmtree(...) / socket.socket(...)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            value = node.func.value
            if isinstance(value, ast.Name):
                module = value.id
                blocked = _BLOCKED_ATTR_CALLS.get(module)
                if blocked and attr in blocked:
                    raise PermissionError(
                        f"RunPython: '{module}.{attr}(...)' 호출 차단. 외부 클라이언트 안전을 위해 "
                        f"destructive / shell 호출 비허용. 분석은 dartlab API · polars · pathlib (읽기) "
                        f"· ~/.dartlab/ · /tmp/ 안의 안전 쓰기로."
                    )

        # ② __import__("os") / __import__("subprocess") 우회
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "__import__":
            if (
                node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
                and node.args[0].value in _BLOCKED_IMPORT_TARGETS
            ):
                raise PermissionError(
                    f"RunPython: __import__('{node.args[0].value}') 우회 차단. "
                    f"호출 가능 attr 만 거부 — import 자체는 허용되지만 dangerous 호출은 막음."
                )

        # ③ from os import system / from subprocess import run 등 destructive 항목 직접 import
        if isinstance(node, ast.ImportFrom) and node.module in _BLOCKED_ATTR_CALLS:
            blocked = _BLOCKED_ATTR_CALLS[node.module]
            for alias in node.names:
                if alias.name == "*" or alias.name in blocked:
                    raise PermissionError(
                        f"RunPython: 'from {node.module} import {alias.name}' 차단. dangerous 항목 직접 import 비허용."
                    )


def _defaultSafeRoots() -> list[str]:
    """파일 쓰기 허용 prefix — ~/.dartlab/, ./tmp/, /tmp/, $TEMP/."""
    home = os.path.expanduser("~")
    roots: list[str] = [
        os.path.join(home, ".dartlab"),
        os.path.abspath("./tmp"),
        tempfile.gettempdir(),
    ]
    if os.path.exists("/tmp"):
        roots.append("/tmp")
    # normpath 로 OS 별 separator 통일.
    return [os.path.normpath(r) for r in roots]


_WRITE_MODE_CHARS = ("w", "a", "x", "+")


def _safeOpenFactory(safe_roots: list[str] | None = None) -> Callable[..., Any]:
    """write/append/create mode 의 path 를 안전 경로로 제한하는 open wrapper.

    read mode (`r`, `rb`) 는 그대로 통과 — 외부 본문 파일 분석 등 정상 use case 보존.
    `+` 도 write 권한 포함이라 검증 대상.
    """
    roots = [os.path.normpath(r) for r in (safe_roots or _defaultSafeRoots())]
    real_open = open  # 캡처 — 안에서 builtin 의존 안 하도록.

    def safe_open(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        if any(ch in mode for ch in _WRITE_MODE_CHARS):
            try:
                path_str = os.fspath(file)
            except TypeError:
                # file descriptor (int) 등 — 검증 못 하지만 user 공격 surface 좁음.
                return real_open(file, mode, *args, **kwargs)
            abs_path = os.path.normpath(os.path.abspath(path_str))
            if not _isUnderSafeRoots(abs_path, roots):
                raise PermissionError(
                    f"RunPython: 파일 쓰기는 안전 경로만 허용 ({', '.join(roots)}). "
                    f"시도된 경로: {abs_path}. 결과 저장은 SaveArtifact 도구 사용 권장."
                )
        return real_open(file, mode, *args, **kwargs)

    return safe_open


def _isUnderSafeRoots(abs_path: str, roots: list[str]) -> bool:
    """abs_path 가 roots 중 하나의 직속/하위 인가."""
    for root in roots:
        if abs_path == root:
            return True
        # path separator 추가해서 prefix-match — 'C:\\Users\\ab' 가 'C:\\Users\\a' 의 하위로 false 매칭 방지.
        if abs_path.startswith(root + os.sep):
            return True
    return False

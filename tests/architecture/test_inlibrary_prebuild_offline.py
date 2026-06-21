"""in-library prebuild stage offline 가드 — ``stages/prebuild.py`` 의 run* 전수.

기존 ``test_prebuild_offline.py`` 는 ``.github/scripts/prebuild/*.py`` 의 ``main()`` 만
검사한다(``_findMainFunc`` = literally ``main`` 이름만). prebuild 오케스트레이션을
in-library ``stages/prebuild.py`` 로 흡수하면 stage 함수(``runMacroJson`` 등)는 ``main``
이 아니므로 그 가드에서 빠진다 — PREBUILD_DIR glob 확장만으로는 ``main`` 부재로 FAIL.

본 평행 테스트는 ``stages/prebuild.py`` 를 AST 파싱해 ``run`` 으로 시작하는 모든
FunctionDef 에 대해:
  (a) 첫 비-docstring stmt 가 ``enforceOffline()`` 호출,
  (b) 모듈 import 가 ``_FORBIDDEN_IMPORTS`` 7종 미포함,
을 단언한다. 헬퍼는 기존 ``test_prebuild_offline.py`` 에서 재사용(중복 0).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.architecture.test_prebuild_offline import (
    _FORBIDDEN_IMPORTS,
    _FORBIDDEN_TOP_LEVEL,
    _callsEnforceOffline,
    _collectImports,
)

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[2]
_PREBUILD_STAGE = _ROOT / "src" / "dartlab" / "pipeline" / "stages" / "prebuild.py"


def _runFuncs(tree: ast.Module) -> list[ast.FunctionDef]:
    return [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith("run")]


def _bodyAfterDocstring(func: ast.FunctionDef) -> list[ast.stmt]:
    body = list(func.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        body = body[1:]
    return body


def test_inlibrary_prebuild_module_exists() -> None:
    """stages/prebuild.py 존재 + run* stage 함수 ≥ 1."""
    assert _PREBUILD_STAGE.exists(), "stages/prebuild.py 부재 — macro prebuild 흡수 미완"
    tree = ast.parse(_PREBUILD_STAGE.read_text(encoding="utf-8"))
    funcs = _runFuncs(tree)
    assert funcs, "stages/prebuild.py 에 run* stage 함수 없음"
    names = {f.name for f in funcs}
    assert "runMacroJson" in names, f"runMacroJson 누락: {sorted(names)}"


def test_inlibrary_prebuild_run_enforces_offline() -> None:
    """stages/prebuild.py 의 모든 run* 함수 첫 비-docstring stmt 가 enforceOffline()."""
    tree = ast.parse(_PREBUILD_STAGE.read_text(encoding="utf-8"))
    for func in _runFuncs(tree):
        body = _bodyAfterDocstring(func)
        assert _callsEnforceOffline(body), (
            f"prebuild.{func.name}(): 진입 5 stmt 안에 enforceOffline() 호출 필요. "
            "외부 API 호출 차단 가드 누락 — prebuild stage = offline only."
        )


def test_inlibrary_prebuild_blocked_imports() -> None:
    """stages/prebuild.py 가 외부 API client / fetcher 모듈 import 금지."""
    tree = ast.parse(_PREBUILD_STAGE.read_text(encoding="utf-8"))
    imports = _collectImports(tree)
    violations: list[str] = []
    for imp in imports:
        for forbidden in _FORBIDDEN_IMPORTS:
            if imp == forbidden or imp.startswith(forbidden + "."):
                violations.append(imp)
                break
        if imp in _FORBIDDEN_TOP_LEVEL:
            violations.append(imp)
    assert not violations, (
        f"stages/prebuild.py: 외부 API import 발견: {violations}. "
        "외부 호출은 sync 단계(stages/macro.py runMacro*)로 옮기시오."
    )

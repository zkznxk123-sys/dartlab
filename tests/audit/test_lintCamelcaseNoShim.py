"""tests/audit/lint_camelcase_ast.py — `--no-shim` 플래그 동작 검증."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parent.parent.parent
_SCRIPT = _REPO / "scripts" / "dev" / "lint_camelcase_ast.py"


def _loadModule():
    """lint_camelcase_ast.py 를 모듈로 동적 로드 (매 호출마다 fresh).

    `sys.modules` 등록 필수 — @dataclass 가 cls.__module__ lookup 시 의존.
    """
    spec = importlib.util.spec_from_file_location("lintCamelMod", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _writeShimFile(path: Path) -> None:
    """`snake_alias = camelOrigin` 패턴 (BC shim) 1 개를 갖는 .py 파일 작성."""
    path.write_text(
        "def fetchPrice():\n    return 1\n\nfetch_price = fetchPrice\n",
        encoding="utf-8",
    )


def test_shimAcceptedByDefault(tmp_path: Path):
    """기본 모드 — `snake_alias = camelOrigin` 은 shim 으로 허용."""
    mod = _loadModule()
    mod._NO_SHIM = False  # 명시 reset (다른 테스트 영향 차단)
    target = tmp_path / "shim_default.py"
    _writeShimFile(target)
    violations = mod._lint_file(target, baseline=True)
    names = [v.name for v in violations if v.kind == "var"]
    assert "fetch_price" not in names, "기본 모드에서는 shim 통과여야 한다."


def test_noShimRejectsAlias(tmp_path: Path):
    """`--no-shim` 활성 (모듈 전역 _NO_SHIM=True) → shim 도 위반으로 잡힘."""
    mod = _loadModule()
    mod._NO_SHIM = True
    target = tmp_path / "shim_strict.py"
    _writeShimFile(target)
    violations = mod._lint_file(target, baseline=True)
    snakeVars = [v.name for v in violations if v.kind == "var" and v.name == "fetch_price"]
    assert snakeVars == ["fetch_price"], (
        f"--no-shim 시 snake_case 변수도 위반이어야 한다. 검출: {[v.name for v in violations]}"
    )

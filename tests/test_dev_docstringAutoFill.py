"""docstringAutoFill 자체 검증 — P-PR2 dev tool.

`scripts/dev/docstringAutoFill.py` 의 핵심 (_hasSection / _isWrapper / _isPureReturnNone /
_renderType / _argNames / _buildStub / _patchFile) 가 fixture 함수에 대해 정확 동작.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parent.parent
_TOOL = _REPO / "scripts" / "dev" / "docstringAutoFill.py"


@pytest.fixture(scope="module")
def tool():
    spec = importlib.util.spec_from_file_location("docstringAutoFill", _TOOL)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["docstringAutoFill"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_has_section_keywords(tool) -> None:
    """Args/Returns/SeeAlso/Requires keyword 변종 매칭."""
    doc = "Args:\n  x: int\n\nReturns:\n  bool"
    assert tool._hasSection(doc, "Args") is True
    assert tool._hasSection(doc, "Returns") is True
    assert tool._hasSection(doc, "SeeAlso") is False
    assert tool._hasSection(doc, "Requires") is False
    # 한국어 변종
    assert tool._hasSection("매개변수:\n  x: int", "Args") is True


def test_is_wrapper(tool) -> None:
    """본문 ≤ 2 stmt + return value → wrapper."""
    func1 = next(n for n in ast.walk(ast.parse("def f():\n    return g()")) if isinstance(n, ast.FunctionDef))
    assert tool._isWrapper(func1) is True
    func2 = next(
        n
        for n in ast.walk(ast.parse("def f():\n    a = 1\n    b = 2\n    return a + b"))
        if isinstance(n, ast.FunctionDef)
    )
    assert tool._isWrapper(func2) is False


def test_is_pure_return_none(tool) -> None:
    func = next(n for n in ast.walk(ast.parse("def f() -> None:\n    pass")) if isinstance(n, ast.FunctionDef))
    assert tool._isPureReturnNone(func) is True
    func2 = next(n for n in ast.walk(ast.parse("def f(x: int) -> None:\n    pass")) if isinstance(n, ast.FunctionDef))
    assert tool._isPureReturnNone(func2) is False


def test_arg_names_renders_types(tool) -> None:
    """signature 의 (name, type_str) 정확 추출 (self/cls 제외)."""
    src = "def f(self, x: int, y: str = 'a', *args: int, **kwargs: str) -> pl.DataFrame: pass"
    func = next(n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef))
    args = tool._argNames(func)
    names = [n for n, _ in args]
    assert names == ["x", "y", "*args", "**kwargs"]
    types = dict(args)
    assert types["x"] == "int"
    assert types["y"] == "str"


def test_build_stub_includes_missing_sections(tool) -> None:
    """누락 섹션만 stub 생성."""
    src = "def f(x: int, y: str) -> bool: pass"
    func = next(n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef))
    missing = {"Args", "Returns", "SeeAlso", "Requires"}
    lines = tool._buildStub(func, missing, ["polars"], indent="    ")
    text = "\n".join(lines)
    assert "Args:" in text
    assert "x: <TODO: param desc> (int)" in text
    assert "Returns:" in text
    assert "<TODO: return desc> (bool)" in text
    assert "SeeAlso:" in text
    assert "Requires:" in text
    assert "- polars" in text


def test_patch_file_dry_run(tool, tmp_path) -> None:
    """dry-run 시 파일 변경 없음."""
    src = tmp_path / "sample.py"
    src.write_text(
        '''
def foo(x: int) -> bool:
    """예시 함수.

    Example:
        >>> foo(1)
    """
    return x > 0
''',
        encoding="utf-8",
    )
    original = src.read_text(encoding="utf-8")
    count, report = tool._patchFile(src, dryRun=True, maxFuncs=10)
    assert count >= 1
    # dry-run 이라 file 그대로
    assert src.read_text(encoding="utf-8") == original


def test_patch_file_apply_inserts_stub(tool, tmp_path) -> None:
    """apply 시 docstring 마지막 \"\"\" 직전에 missing 섹션 stub 삽입.

    fixture 함수는 본문 3 stmt 이상 — wrapper 면제 회피해서 4 섹션 모두 stub 삽입 확인.
    """
    src = tmp_path / "sample.py"
    src.write_text(
        '''
def foo(x: int) -> bool:
    """예시 함수.

    Example:
        >>> foo(1)
    """
    if x < 0:
        return False
    result = x > 0
    return result
''',
        encoding="utf-8",
    )
    count, report = tool._patchFile(src, dryRun=False, maxFuncs=10)
    assert count == 1
    patched = src.read_text(encoding="utf-8")
    assert "Args:" in patched
    assert "Returns:" in patched
    assert "SeeAlso:" in patched
    assert "Requires:" in patched
    # 기존 Example 섹션 보존
    assert "Example:" in patched
    assert ">>> foo(1)" in patched

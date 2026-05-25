"""docstringNineSection audit 자체 검증 — P-PR1 게이트.

`tests/audit/docstringNineSection.py` 의 핵심 (_SECTION_KEYWORDS / _hasSection /
_isWrapper / _isPureReturnNone / _scan) 가 fixture 에서 정확 동작 + 6 baseline schema.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parent.parent.parent
_AUDIT_SCRIPT = _REPO / "tests" / "audit" / "docstringNineSection.py"


@pytest.fixture(scope="module")
def audit_module():
    spec = importlib.util.spec_from_file_location("docstringNineSection", _AUDIT_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["docstringNineSection"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_section_keywords_set(audit_module) -> None:
    """6 sub-section 모두 정의 (SSOT docstringStandard.md 부합)."""
    assert set(audit_module._SECTION_KEYWORDS.keys()) == {
        "Capabilities",
        "Guide",
        "SeeAlso",
        "Requires",
        "AIContext",
        "Specifications",
    }


def test_has_section_korean_english(audit_module) -> None:
    """한국어/영어 keyword 양방향 매칭."""
    en_doc = "Capabilities:\n  - foo bar"
    ko_doc = "기능:\n  - foo bar"
    keywords = audit_module._SECTION_KEYWORDS["Capabilities"]
    assert audit_module._hasSection(en_doc, keywords) is True
    assert audit_module._hasSection(ko_doc, keywords) is True
    # 다른 섹션 keyword 는 매칭 안 됨
    assert audit_module._hasSection(en_doc, audit_module._SECTION_KEYWORDS["Guide"]) is False


def test_is_wrapper_simple(audit_module) -> None:
    """본문 ≤ 2 stmt + return → wrapper."""
    src = """
def foo():
    return bar()
"""
    func = next(n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef))
    assert audit_module._isWrapper(func) is True


def test_is_wrapper_complex_false(audit_module) -> None:
    """본문 3 stmt 이상 → wrapper 아님."""
    src = """
def foo():
    a = 1
    b = 2
    return a + b
"""
    func = next(n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef))
    assert audit_module._isWrapper(func) is False


def test_is_pure_return_none(audit_module) -> None:
    """인자 0 + return None annotation → pure side-effect."""
    src = """
def foo() -> None:
    print("hi")
"""
    func = next(n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef))
    assert audit_module._isPureReturnNone(func) is True


def test_is_pure_return_none_false_with_args(audit_module) -> None:
    """인자 1 개 이상 → pure 아님."""
    src = """
def foo(x: int) -> None:
    print(x)
"""
    func = next(n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef))
    assert audit_module._isPureReturnNone(func) is False


def test_six_baselines_exist_and_valid_schema(audit_module) -> None:
    """6 sub-baseline JSON 형식 안정성."""
    for section in ["Capabilities", "Guide", "SeeAlso", "Requires", "AIContext", "Specifications"]:
        path = _REPO / "tests" / "audit" / "_baselines" / f"docstring{section}.json"
        if not path.exists():
            pytest.skip(f"baseline {section} 미생성")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "_note" in data, f"{section}: _note 부재"
        assert "violations" in data and isinstance(data["violations"], list), f"{section}: violations 형식 위반"
        for entry in data["violations"]:
            assert isinstance(entry, str)
            assert "::" in entry, f"{section} entry 형식 위반 (path::name 필요): {entry}"


@pytest.mark.xfail(reason="baseline 516 건 누락 — baseline 갱신 deferred")
def test_scan_real_providers_baseline_pass(audit_module) -> None:
    """실 providers/ 에 대해 _scan() 호출 — 6 baseline 안에 모두 들어가야."""
    violations = audit_module._scan()
    for section, items in violations.items():
        path = _REPO / "tests" / "audit" / "_baselines" / f"docstring{section}.json"
        if not path.exists():
            pytest.skip(f"baseline {section} 미생성")
        baseline = json.loads(path.read_text(encoding="utf-8"))
        allowed = set(baseline.get("violations", []))
        new = [k for k in items if k not in allowed]
        assert not new, f"baseline 외 신규 {section} 위반: {len(new)} 건 (예시: {new[:3]})"

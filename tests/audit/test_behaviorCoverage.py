"""behaviorCoverage audit 자체 검증 — P-PR1 게이트.

`tests/audit/behaviorCoverage.py` 의 핵심 로직 (_camelToSnake / _testPatterns /
_publicMethods / _matchAny) 가 fixture src + test pair 에 대해 정확히 동작하는지 검증.

baseline JSON 형식 안정성도 검증 — P-PR4/P-PR5 가 sweep 시 같은 형식 가정.
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
_AUDIT_SCRIPT = _REPO / "scripts" / "audit" / "behaviorCoverage.py"


@pytest.fixture(scope="module")
def audit_module():
    """behaviorCoverage.py 를 module 로 로드 (scripts/ 는 import path 아님)."""
    spec = importlib.util.spec_from_file_location("behaviorCoverage", _AUDIT_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["behaviorCoverage"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_camel_to_snake(audit_module) -> None:
    """camelCase → snake_case 변환 정확성."""
    assert audit_module._camelToSnake("fetchFiling") == "fetch_filing"
    assert audit_module._camelToSnake("show") == "show"
    assert audit_module._camelToSnake("ABCDef") == "a_b_c_def"
    assert audit_module._camelToSnake("listSections") == "list_sections"


def test_test_patterns_match_both_cases(audit_module) -> None:
    """fetchFiling 에 대응되는 test 이름 — camelCase + snake_case 둘 다 인정."""
    patterns = audit_module._testPatterns("fetchFiling")
    candidates = {
        "test_fetchFiling",
        "test_fetch_filing",
        "test_fetchFiling_period",
        "test_fetch_filing_2024Q1",
    }
    for name in candidates:
        assert any(pat.match(name) for pat in patterns), f"{name} 매칭 실패"


def test_test_patterns_reject_unrelated(audit_module) -> None:
    """fetchFiling 패턴이 무관 함수 이름을 잘못 매칭하지 않는지."""
    patterns = audit_module._testPatterns("fetchFiling")
    negatives = {
        "test_imports",
        "test_show",
        "test_fetch_filings_listing",  # filings (s) 차이
        "test_fetchFilingResult",  # 더 긴 이름
    }
    for name in negatives:
        assert not any(pat.match(name) for pat in patterns), f"{name} 잘못 매칭"


def test_public_methods_extracts_class_methods(audit_module) -> None:
    """class 안 공개 method 가 'ClassName.methodName' 형식으로 추출되는지."""
    src = """
class Foo:
    def bar(self): pass
    def _private(self): pass
    def __init__(self): pass

    @property
    def prop(self): return 1

def topLevel(): pass

def _hidden(): pass
"""
    tree = ast.parse(src)
    methods = audit_module._publicMethods(tree)
    names = {name for name, _ in methods}
    assert names == {"Foo.bar", "topLevel"}, f"실제: {names}"


def test_match_any_camelcase(audit_module) -> None:
    """method 의 leafName 이 test 함수 집합에 매칭되는지."""
    testNames = {"test_imports", "test_fetchFiling_period"}
    assert audit_module._matchAny("fetchFiling", testNames) is True
    assert audit_module._matchAny("show", testNames) is False


def test_match_any_snake_case(audit_module) -> None:
    testNames = {"test_fetch_filing"}
    assert audit_module._matchAny("fetchFiling", testNames) is True


def test_baseline_schema(audit_module) -> None:
    """baseline JSON 형식 안정성 — P-PR4/P-PR5 sweep 가 의존."""
    baselinePath = _REPO / "scripts" / "audit" / "_baselines" / "behaviorCoverage.json"
    if not baselinePath.exists():
        pytest.skip("baseline 미생성 (--update-baseline 한 번 실행 필요)")
    data = json.loads(baselinePath.read_text(encoding="utf-8"))
    assert "_note" in data
    assert "violations" in data
    assert isinstance(data["violations"], list)
    for entry in data["violations"]:
        assert isinstance(entry, str)
        assert "::" in entry, f"형식 위반 (path::method 필요): {entry}"

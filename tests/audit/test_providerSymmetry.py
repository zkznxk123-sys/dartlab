"""providerSymmetry audit 자체 검증 — P-PR1 게이트.

`tests/audit/providerSymmetry.py` 의 핵심 (_DART_ONLY / _EDINET_DEFERRED / _bodyLoc /
_collectPublicMethods / _scan) 가 fixture 또는 실 dart/edgar company 에 대해 정확 동작.
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
_AUDIT_SCRIPT = _REPO / "scripts" / "audit" / "providerSymmetry.py"


@pytest.fixture(scope="module")
def audit_module():
    spec = importlib.util.spec_from_file_location("providerSymmetry", _AUDIT_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["providerSymmetry"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_dart_only_set_non_empty(audit_module) -> None:
    """`_DART_ONLY` 는 dart 한국 특화 18 메서드 + raw* 3 = 20 항목 이상 (`runtime.providerProtocol` SSOT)."""
    assert len(audit_module._DART_ONLY) >= 18
    # 핵심 항목 sanity check
    assert "codeName" in audit_module._DART_ONLY
    assert "keywordTrend" in audit_module._DART_ONLY
    assert "credit" in audit_module._DART_ONLY


def test_edinet_deferred_set(audit_module) -> None:
    """`_EDINET_DEFERRED` = 5 method 사용자 명시 deferred."""
    assert audit_module._EDINET_DEFERRED == frozenset({"ask", "quant", "disclosure", "liveFilings", "readFiling"})


def test_body_loc_basic(audit_module) -> None:
    """`_bodyLoc` 는 함수 body 줄 수를 정확히 (end_lineno - lineno + 1)."""
    src = """
def foo():
    a = 1
    b = 2
    return a + b
"""
    tree = ast.parse(src)
    func = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
    assert audit_module._bodyLoc(func) == 4  # def + 3 body lines


def test_collect_public_methods_filters_underscore_and_property(audit_module, tmp_path) -> None:
    """클래스 안 method 추출 시 underscore/dunder/property 제외."""
    fixture = tmp_path / "company.py"
    fixture.write_text(
        """
class Company:
    def show(self):
        return 1

    def _private(self):
        return 2

    def __init__(self):
        pass

    @property
    def name(self):
        return "x"

    def select(self):
        return None

class Helper:
    def notACompanyMethod(self):
        return 1
""",
        encoding="utf-8",
    )
    methods = audit_module._collectPublicMethods(fixture)
    # 클래스 이름이 "Company" 인 것만 + underscore/property 제외
    assert set(methods.keys()) == {"show", "select"}


def test_baseline_schema(audit_module) -> None:
    """baseline JSON 형식 안정성 — P-PR6/7/8 가 의존."""
    baselinePath = _REPO / "scripts" / "audit" / "_baselines" / "providerSymmetry.json"
    if not baselinePath.exists():
        pytest.skip("baseline 미생성")
    data = json.loads(baselinePath.read_text(encoding="utf-8"))
    assert "_note" in data
    assert "missing" in data and isinstance(data["missing"], list)
    assert "shallow" in data and isinstance(data["shallow"], list)


def test_scan_real_dart_edgar(audit_module) -> None:
    """실 dart/edgar company.py 에 대해 _scan() 호출 — baseline 안 통과해야."""
    missing, shallow = audit_module._scan()
    baselinePath = _REPO / "scripts" / "audit" / "_baselines" / "providerSymmetry.json"
    if not baselinePath.exists():
        pytest.skip("baseline 미생성")
    baseline = json.loads(baselinePath.read_text(encoding="utf-8"))
    allowed_missing = set(baseline.get("missing", []))
    allowed_shallow = set(baseline.get("shallow", []))
    new_missing = [m for m in missing if m not in allowed_missing]
    new_shallow = [s for s in shallow if s not in allowed_shallow]
    assert not new_missing, f"baseline 외 신규 missing: {new_missing}"
    assert not new_shallow, f"baseline 외 신규 shallow: {new_shallow}"

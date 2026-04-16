"""Phase 15 A2 — 데이터 신뢰도 sentinel (foundation audit 46 부채 회귀 가드)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parent.parent / "src" / "dartlab"


@pytest.mark.unit
def test_no_direct_q4_read_in_tax_analysis():
    """Phase 15 A1: taxAnalysis 가 annualSumFlow 사용 (Q4 함정 차단)."""
    src = (_SRC / "analysis" / "financial" / "taxAnalysis.py").read_text(encoding="utf-8")
    assert "annualSumFlow" in src, "taxAnalysis 가 annualSumFlow 사용 안 함 (Q4 함정)"


@pytest.mark.unit
def test_no_direct_q4_read_in_prediction_signals():
    """Phase 15 A1: predictionSignals Sloan calc 가 annualSumFlow 사용."""
    src = (_SRC / "analysis" / "financial" / "predictionSignals.py").read_text(encoding="utf-8")
    assert "annualSumFlow" in src, "predictionSignals 가 annualSumFlow 사용 안 함"


@pytest.mark.unit
def test_no_direct_q4_read_in_macro_exposure():
    """Phase 15 A1: macroExposure 가 annualSumFlow 사용."""
    src = (_SRC / "analysis" / "financial" / "macroExposure.py").read_text(encoding="utf-8")
    assert "annualSumFlow" in src, "macroExposure 가 annualSumFlow 사용 안 함"


@pytest.mark.unit
def test_flow_ssot_exists():
    """core/finance/flow.py 의 annualSumFlow 가 SSOT 로 존재."""
    from dartlab.core.finance.flow import annualSumFlow, synthesizeAnnualFromQuarters

    assert callable(annualSumFlow)
    assert callable(synthesizeAnnualFromQuarters)


@pytest.mark.unit
def test_annual_sum_flow_basic():
    """annualSumFlow 4분기 합산 기본 동작."""
    from dartlab.core.finance.flow import annualSumFlow

    data = {"2025Q1": 10, "2025Q2": 12, "2025Q3": 14, "2025Q4": 16}
    result = annualSumFlow(data, "2025Q4", set(data.keys()))
    assert result == 52.0, f"4분기 합산 실패: {result}"

    # annual 컬럼은 그대로 반환
    data2 = {"2024": 100, "2025Q4": 20}
    result2 = annualSumFlow(data2, "2024", set(data2.keys()))
    assert result2 == 100, "annual 컬럼 그대로 반환 실패"


@pytest.mark.unit
def test_annual_sum_flow_cumulative_fallback():
    """annualSumFlow 누적공시 fallback (배당 Q4 단독)."""
    from dartlab.core.finance.flow import annualSumFlow

    # Q1~Q3 None, Q4 만 50 → 누적공시로 간주, 50 그대로
    data = {"2025Q1": None, "2025Q2": None, "2025Q3": None, "2025Q4": 50}
    result = annualSumFlow(data, "2025Q4", set(data.keys()), withFallback=True)
    assert result == 50.0, f"누적공시 fallback 실패: {result}"


@pytest.mark.unit
def test_no_duplicate_get_helpers_in_financial():
    """Phase 16 B2: analysis/financial 하위 `_get`/`_getF*` 정의가 SSOT 로 0 건.

    `from dartlab.core.finance.safe import get as _get` alias 만 허용.
    `def _get(...)` / `def _getF[0-9]*(...)` 은 복붙 중복 — 금지.

    예외: scenarioSensitivity.py `_get(row_key: str)` 는 시그니처가 다름 (1-arg str lookup).
    """
    financial_dir = _SRC / "analysis" / "financial"
    pattern = re.compile(r"^def\s+_get(F\d*)?\s*\(\s*row\b", re.MULTILINE)

    violations = []
    for py in financial_dir.glob("*.py"):
        src = py.read_text(encoding="utf-8")
        for m in pattern.finditer(src):
            violations.append(f"{py.name}: {m.group(0)}")

    assert not violations, (
        "analysis/financial 에 중복 _get/_getF* 정의 발견 — "
        "core.finance.safe.get 를 사용하세요:\n" + "\n".join(violations)
    )


@pytest.mark.unit
def test_safe_module_is_ssot():
    """Phase 16 B1: core/finance/safe.py 가 3 함수 SSOT 로 노출."""
    from dartlab.core.finance.safe import get, getFirst, yoy

    assert callable(get)
    assert callable(getFirst)
    assert callable(yoy)

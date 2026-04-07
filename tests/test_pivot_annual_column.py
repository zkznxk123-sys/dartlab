"""Sentinel — Layer A pivot annual 컬럼 자동 노출 회귀 차단.

dartlab `c.IS / c.CIS / c.CF` 가 분기 컬럼 + annual 컬럼 둘 다 노출해야 함
(`_finance_helpers.py::_financeToDataFrame`).

회귀: pivot 결과에 annual 컬럼이 사라지면 calc 함수가 ttmSum 우회 못 함.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.requires_data]


def test_dart_is_has_annual_column():
    """SK하이닉스 IS 가 분기 + annual 컬럼 둘 다 노출."""
    import dartlab

    c = dartlab.Company("000660")
    df = c.IS
    assert df is not None

    cols = df.columns
    qCols = [c for c in cols if "Q" in c and c.replace("Q", "")[:5].isdigit() is False]
    annCols = [c for c in cols if c.isdigit() and len(c) == 4]

    assert any("Q" in c for c in cols), "분기 컬럼이 사라짐"
    assert len(annCols) > 0, f"annual 컬럼이 없음. cols={cols}"
    # 최소 2025 또는 가장 최근 연도 annual
    assert "2025" in cols or "2024" in cols, f"annual 컬럼에 최근 연도 없음. cols={cols}"


def test_dart_is_annual_equals_quarter_sum():
    """annual 컬럼 = Q1+Q2+Q3+Q4 합 (None-safe)."""
    import dartlab

    c = dartlab.Company("000660")
    df = c.IS
    assert df is not None

    rev = df.filter(df["계정명"] == "매출액")
    assert rev.height > 0

    annual2025 = rev["2025"][0]
    q1 = rev["2025Q1"][0]
    q2 = rev["2025Q2"][0]
    q3 = rev["2025Q3"][0]
    q4 = rev["2025Q4"][0]

    expectedSum = sum(v for v in [q1, q2, q3, q4] if v is not None)
    assert annual2025 == expectedSum, f"annual={annual2025} vs Q합={expectedSum}"
    # SK하이닉스 2025 매출 ≈ 97.1조
    assert 95e12 < annual2025 < 100e12


def test_dart_bs_annual_equals_q4():
    """BS annual 컬럼 = Q4 (연말잔액 alias)."""
    import dartlab

    c = dartlab.Company("000660")
    df = c.BS
    assert df is not None

    ta = df.filter(df["계정명"] == "자산총계")
    assert ta.height > 0

    annual2025 = ta["2025"][0]
    q4 = ta["2025Q4"][0]
    assert annual2025 == q4, f"BS annual={annual2025} vs Q4={q4} (BS 는 alias 여야 함)"


def test_annual_col_first_in_annualColsFromPeriods():
    """annualColsFromPeriods 가 annual 컬럼 우선 (Q4 fallback 아님)."""
    import dartlab
    from dartlab.analysis.financial._helpers import annualColsFromPeriods, isQuarterlyFallback, toDict

    c = dartlab.Company("000660")
    parsed = toDict(c.select("IS", ["매출액"]))
    assert parsed is not None
    _, periods = parsed

    yCols = annualColsFromPeriods(periods)
    assert yCols[0].isdigit(), f"annualColsFromPeriods[0] = {yCols[0]} (expected 4자리 연도, Q4 fallback 아님)"
    assert not isQuarterlyFallback(yCols), "annual 컬럼 노출 시 quarterlyFallback=False"

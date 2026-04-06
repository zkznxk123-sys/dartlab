"""R24 audit 회귀 테스트 — analysis 엔진.

R24-1: c.analysis(group, sub) 에서 sub 가 group 에 속하지 않으면 ValueError.
이전엔 silent 로 잘못된 그룹의 결과를 반환했다.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_analysis_rejects_axis_outside_group():
    """R24-1: 그룹/축 mismatch 시 silent 가 아닌 명시적 ValueError."""
    from dartlab.analysis.financial import Analysis

    a = Analysis()

    # company 없이도 검증 발생해야 함 (그룹 검증은 sub 해석 직후)
    # 단 company 없이는 listCalcs 까지 가므로 company 동봉
    class _MockCompany:
        stockCode = "000000"
        market = "KR"

    with pytest.raises(ValueError, match="속하지 않습니다"):
        a("valuation", "수익성", company=_MockCompany())


def test_analysis_rejects_financial_axis_in_valuation():
    """R24-1: financial 그룹 축을 valuation 그룹으로 호출하면 거부."""
    from dartlab.analysis.financial import Analysis

    a = Analysis()

    class _MockCompany:
        stockCode = "000000"
        market = "KR"

    for axis in ["안정성", "성장성", "현금흐름", "수익구조"]:
        with pytest.raises(ValueError, match="속하지 않습니다"):
            a("valuation", axis, company=_MockCompany())


def test_analysis_accepts_correct_group_axis():
    """R24-1: 정상 그룹/축 조합은 통과 (회귀 0 확인)."""
    from dartlab.analysis.financial import Analysis

    a = Analysis()
    # company 없이는 _listCalcs 까지만 호출되므로 ValueError 안 나야 함
    result = a("financial", "수익성")
    # company 없으면 calc 목록 DataFrame 반환
    assert result is not None


def test_analysis_unknown_axis_explicit_error():
    """기존 동작 — 없는 축은 ValueError (회귀 0 확인)."""
    from dartlab.analysis.financial import Analysis

    a = Analysis()
    with pytest.raises(ValueError, match="알 수 없는 분석 축"):
        a("financial", "없는축")


def test_analysis_guide_returns_dataframe():
    """무인자 → 가이드 DataFrame (회귀 0 확인)."""
    import polars as pl

    from dartlab.analysis.financial import Analysis

    a = Analysis()
    guide = a()
    assert isinstance(guide, pl.DataFrame)
    assert "axis" in guide.columns
    assert "items" in guide.columns
    assert len(guide) >= 14

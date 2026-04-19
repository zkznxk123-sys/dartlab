"""analysis 엔진 실제 데이터 스모크 — c.analysis(axis) 핵심 축."""

from __future__ import annotations

import polars as pl
import pytest


@pytest.mark.realData
@pytest.mark.integration
class TestAnalysisEngine:
    """c.analysis 의 공식 진입점이 실제 데이터로 None 없이 동작."""

    def test_overview_returnsDataFrame(self, samsungRealData):
        """c.analysis() → 전체 분석 DataFrame."""
        result = samsungRealData.analysis()
        assert result is not None
        assert isinstance(result, pl.DataFrame)
        assert result.height > 0

    def test_profitability_returnsDict(self, samsungRealData):
        result = samsungRealData.analysis("profitability")
        assert result is not None
        assert isinstance(result, dict)
        assert result, "profitability 결과가 빈 dict"

    def test_stability_returnsDict(self, samsungRealData):
        result = samsungRealData.analysis("stability")
        assert result is not None
        assert isinstance(result, dict)

    def test_growth_returnsDict(self, samsungRealData):
        result = samsungRealData.analysis("growth")
        assert result is not None
        assert isinstance(result, dict)

    def test_invalidAxis_gracefulFailure(self, samsungRealData):
        """존재하지 않는 axis 는 조용히 실패하지 말고 명시적으로 에러."""
        with pytest.raises((ValueError, KeyError, AttributeError, TypeError)):
            samsungRealData.analysis("definitely_not_an_axis_xyz")

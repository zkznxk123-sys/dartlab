"""Industry lifecycle clock unit 테스트.

순수 로직 (classifyPhase) + 빈 industryId 안전 처리 (classifyLifecycle).
실 산업 데이터 검증은 realData 테스트로 분리.
"""

from __future__ import annotations

import math

import pytest

pytestmark = [pytest.mark.unit]


# ════════════════════════════════════════
# classifyPhase — Vernon 3-phase + 쇠퇴 룰
# ════════════════════════════════════════


class TestClassifyPhase:
    def test_introduction_threshold(self):
        from dartlab.industry.calcs.lifecycle import classifyPhase

        assert classifyPhase(40.0) == "도입"
        assert classifyPhase(30.0) == "도입"  # boundary inclusive

    def test_growth_band(self):
        from dartlab.industry.calcs.lifecycle import classifyPhase

        assert classifyPhase(29.99) == "성장"
        assert classifyPhase(20.0) == "성장"
        assert classifyPhase(10.0) == "성장"  # boundary inclusive

    def test_maturity_band(self):
        from dartlab.industry.calcs.lifecycle import classifyPhase

        assert classifyPhase(9.99) == "성숙"
        assert classifyPhase(5.0) == "성숙"
        assert classifyPhase(0.0) == "성숙"  # boundary inclusive

    def test_decline_band(self):
        from dartlab.industry.calcs.lifecycle import classifyPhase

        assert classifyPhase(-0.01) == "쇠퇴"
        assert classifyPhase(-5.0) == "쇠퇴"
        assert classifyPhase(-50.0) == "쇠퇴"

    def test_unknown_for_none(self):
        from dartlab.industry.calcs.lifecycle import classifyPhase

        assert classifyPhase(None) == "unknown"

    def test_unknown_for_nan(self):
        from dartlab.industry.calcs.lifecycle import classifyPhase

        assert classifyPhase(math.nan) == "unknown"


# ════════════════════════════════════════
# classifyLifecycle — empty industry 안전 처리
# ════════════════════════════════════════


class TestClassifyLifecycleEmpty:
    def test_unknown_industryId_returns_empty_df_with_schema(self):
        """존재하지 않는 industryId → 빈 DataFrame (스키마는 유지)."""
        from dartlab.industry.calcs.lifecycle import classifyLifecycle

        df = classifyLifecycle("__nonexistent_industry_zzz__")
        assert df.height == 0
        # schema 유지 — 다운스트림에서 컬럼 접근 시 KeyError 방지
        assert set(df.columns) == {"연도", "매출(조)", "기업수", "yoy성장률", "phase"}

    def test_industry_callable_lifecycle_flag_routes(self):
        """Industry.__call__ 의 lifecycle=True 가 classifyLifecycle 로 라우팅."""
        from dartlab.industry import Industry

        ind = Industry()
        df = ind("__nonexistent_industry_zzz__", lifecycle=True)
        assert df.height == 0
        assert set(df.columns) == {"연도", "매출(조)", "기업수", "yoy성장률", "phase"}

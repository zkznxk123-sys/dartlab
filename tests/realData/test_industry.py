"""industry 엔진 실제 데이터 스모크 — 산업 맵."""

from __future__ import annotations

import pytest


@pytest.mark.realData
@pytest.mark.integration
class TestIndustryEngine:
    def test_industryClassify_callable(self):
        # dartlab.industry 는 Industry() 인스턴스 (callable) — 가이드 제공.
        # classify 는 industry.sector 모듈의 pure 함수 — 공개 API 로 re-export.
        import dartlab

        assert callable(dartlab.industry)  # Industry() 인스턴스 자체 호출
        from dartlab.industry import classify

        assert callable(classify)

    def test_companyIndustry_resolves(self, samsungRealData):
        """Company.industry 가 실제 산업 정보로 연결."""
        ind = samsungRealData.industry
        assert ind is not None
        # industry 접근은 dict/객체/string 모두 허용 — 단 빈 값은 NG
        if hasattr(ind, "__len__"):
            assert len(ind) > 0

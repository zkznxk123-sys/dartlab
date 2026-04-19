"""industry 엔진 실제 데이터 스모크 — 산업 맵."""

from __future__ import annotations

import pytest


@pytest.mark.realData
@pytest.mark.integration
class TestIndustryEngine:
    def test_industryClassify_callable(self):
        import dartlab

        assert callable(dartlab.industry.classify)

    def test_companyIndustry_resolves(self, samsungRealData):
        """Company.industry 가 실제 산업 정보로 연결."""
        ind = samsungRealData.industry
        assert ind is not None
        # industry 접근은 dict/객체/string 모두 허용 — 단 빈 값은 NG
        if hasattr(ind, "__len__"):
            assert len(ind) > 0

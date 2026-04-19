"""credit 엔진 실제 데이터 스모크 — 신용/부채 분석."""

from __future__ import annotations

import pytest

from tests.conftest import SAMSUNG


@pytest.mark.realData
@pytest.mark.integration
class TestCreditEngine:
    def test_credit_topLevelCallable(self, samsungRealData):
        """dartlab.credit(stockCode) 가 실제 재무로 dict 반환."""
        import dartlab

        result = dartlab.credit(SAMSUNG)
        assert result is not None
        assert isinstance(result, dict)
        assert result, "credit 결과 빈 dict"

    def test_credit_onCompany(self, samsungRealData):
        """c.credit 경유 접근도 동작."""
        result = samsungRealData.credit
        # credit 은 property 일 수도, callable 일 수도 있음
        if callable(result):
            result = result()
        assert result is not None

"""quant 엔진 실제 데이터 스모크 — 가치평가/기술지표."""

from __future__ import annotations

import pytest


@pytest.mark.realData
@pytest.mark.integration
class TestQuantEngine:
    def test_quant_callable(self):
        import dartlab

        assert callable(dartlab.quant)

    def test_quantOnCompany_returnsData(self, samsungRealData):
        """c.quant 가 크래시 없이 실행."""
        q = samsungRealData.quant
        if callable(q):
            q = q()
        # quant 는 dict/DataFrame/object 모두 가능 — None 만 아니면 됨
        assert q is not None

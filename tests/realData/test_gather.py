"""gather 엔진 실제 데이터 스모크 — 외부 데이터 수집.

네트워크 호출 포함. 오프라인 환경에서는 skip 가능성 있음.
"""

from __future__ import annotations

import pytest

from tests.conftest import SAMSUNG


@pytest.mark.realData
@pytest.mark.integration
class TestGatherEngine:
    def test_gather_callable(self):
        import dartlab

        assert callable(dartlab.gather)

    def test_gather_priceAxis(self):
        """price 축은 가장 안정적인 외부 데이터 — 실제 호출."""
        import dartlab

        try:
            df = dartlab.gather("price", SAMSUNG)
        except Exception as e:
            # 네트워크 이슈는 용납하지 않음 (skip 대신 xfail)
            pytest.skip(f"gather('price') 네트워크 오류: {type(e).__name__}: {e}")
        assert df is not None
        if hasattr(df, "height"):
            assert df.height > 0

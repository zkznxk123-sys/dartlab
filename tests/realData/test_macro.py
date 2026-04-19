"""macro 엔진 실제 데이터 스모크 — 거시경제 지표.

ECOS/FRED API 키 필요. 키 없으면 자동 skip.
"""

from __future__ import annotations

import os

import pytest


@pytest.mark.realData
@pytest.mark.integration
class TestMacroEngine:
    def test_macro_callable(self):
        """dartlab.macro 가 호출 가능한지."""
        import dartlab

        assert callable(dartlab.macro)

    def test_macro_axisRuns(self):
        """대표 거시 축 1개를 실제 호출. 키 없으면 skip.

        conftest autouse fixture 가 ECOS/FRED 에 'test_dummy' 를 주입하므로
        단순 존재 체크로는 진짜 키 여부를 구분 못한다 — 값도 검증한다.
        """
        import dartlab

        def _realKey(name: str) -> bool:
            val = os.environ.get(name, "")
            return bool(val) and val != "test_dummy"

        if not any(_realKey(k) for k in ("ECOS_API_KEY", "FRED_API_KEY")):
            pytest.skip("ECOS/FRED API 키 없음 — macro 실제 호출 불가")
        # "rates" 는 실제 등록된 축 (한글 alias "금리" 와 매핑)
        try:
            result = dartlab.macro("rates")
        except Exception as e:
            pytest.fail(f"macro('rates') 크래시: {type(e).__name__}: {e}")
        assert result is not None

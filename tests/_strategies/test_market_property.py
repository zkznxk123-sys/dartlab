"""core/market hypothesis property — T6-1."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st


@pytest.mark.unit
class TestMarketProperty:
    """detectMarket / resolveMarket property 5."""

    @given(code=st.text(alphabet="0123456789", min_size=6, max_size=6))
    def test_korean_6digit_returns_kr(self, code: str) -> None:
        from dartlab.core.market import detectMarket

        assert detectMarket(code) == "KR"

    @given(code=st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=1, max_size=5))
    def test_alpha_code_returns_us(self, code: str) -> None:
        from dartlab.core.market import detectMarket

        assert detectMarket(code) == "US"

    @given(code=st.text(alphabet="0123456789", min_size=6, max_size=6))
    def test_detect_idempotent(self, code: str) -> None:
        from dartlab.core.market import detectMarket

        assert detectMarket(code) == detectMarket(code)

    @given(code=st.text(min_size=1, max_size=10))
    def test_detect_returns_known_label(self, code: str) -> None:
        from dartlab.core.market import detectMarket

        try:
            result = detectMarket(code)
            assert result in {"KR", "US", "JP", "UNKNOWN"}
        except (ValueError, KeyError):
            pass

    @given(code=st.text(alphabet="ABCDEFGHIJ", min_size=1, max_size=4))
    def test_resolve_auto_falls_through(self, code: str) -> None:
        from dartlab.core.market import resolveMarket

        assert resolveMarket(code, "auto") in {"US", "KR", "JP", "UNKNOWN"}

"""core/formatting hypothesis property — T6-1 트랙 (2/5 모듈).

formatComma / formatKr / formatDecimal 의 property.
"""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from tests._strategies import financial_amount


@pytest.mark.unit
class TestFormattingProperty:
    """core/formatting property 7 가지."""

    @given(value=financial_amount)
    def test_format_comma_returns_string(self, value: object) -> None:
        from dartlab.core.formatting import formatComma

        result = formatComma(value)
        assert isinstance(result, str)

    @given(value=financial_amount)
    def test_format_comma_idempotent_on_int(self, value: object) -> None:
        """같은 input → 같은 output."""
        from dartlab.core.formatting import formatComma

        assert formatComma(value) == formatComma(value)

    @given(value=st.none())
    def test_format_comma_null_returns_nullstr(self, value: object) -> None:
        from dartlab.core.formatting import formatComma

        assert formatComma(value, nullStr="-") == "-"
        assert formatComma(value, nullStr="N/A") == "N/A"

    @given(value=financial_amount)
    def test_format_kr_returns_string(self, value: object) -> None:
        from dartlab.core.formatting import formatKr

        result = formatKr(value)
        assert isinstance(result, str)

    @given(value=financial_amount)
    def test_format_kr_with_won_contains_won(self, value: object) -> None:
        from dartlab.core.formatting import formatKr

        result = formatKr(value, withWon=True)
        # nullStr 경우 제외
        if result != "-":
            assert "원" in result or result == "0원" or "-" in result

    @given(value=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False))
    def test_format_comma_decimals_consistent(self, value: float) -> None:
        from dartlab.core.formatting import formatComma

        result0 = formatComma(value, decimals=0)
        result2 = formatComma(value, decimals=2)
        # decimals=0 결과 + decimals=2 결과는 같은 정수부 가짐
        assert result0.split(".")[0] == result2.split(".")[0]

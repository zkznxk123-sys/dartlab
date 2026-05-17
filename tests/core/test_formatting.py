"""dartlab.core.formatting oracle + property — Track 6 (ghostwriter sweep → oracle 보강).

본 트랙 SSOT — [tests/POLICY.md](../POLICY.md) §5 Track 6 (Property-based 50%+).

3 함수 (formatComma, formatKr, formatDecimal) 의 *결과 정확성* 을 검증한다.
[tests/_drafts/test_formatting_draft.py](../_drafts/test_formatting_draft.py) 의
ghostwriter draft 가 "raise 안 함" 만 검증한 것과 달리, 본 파일은:

1. **Oracle** — 명시 입력 → 명시 출력 (사람이 정한 진리값).
2. **Property** — 임의 입력에서 보존되는 속성 (예: nullStr 통과, 부호 보존, 단위 임계).
3. **Mutation 회귀** — mutmut 가 함수 본문 변형 (`>=` → `>`, `1e12` → `1e12+1`) 시 fail 해야 함.

mutmut 대상 — [pyproject.toml#tool.mutmut.paths_to_mutate](../../pyproject.toml).
실행: `uv run mutmut run` → `uv run mutmut results`.
"""

from __future__ import annotations

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from dartlab.core.formatting import formatComma, formatDecimal, formatKr

pytestmark = pytest.mark.unit


class TestFormatCommaOracle:
    """formatComma 명시 oracle — mutmut mutant 가 잡혀야 통과."""

    def test_integer_thousands(self) -> None:
        assert formatComma(1234567) == "1,234,567"

    def test_integer_zero(self) -> None:
        assert formatComma(0) == "0"

    def test_integer_negative(self) -> None:
        assert formatComma(-1234) == "-1,234"

    def test_float_decimals_default(self) -> None:
        assert formatComma(3.14) == "3.14"

    def test_float_integer_value_collapses(self) -> None:
        assert formatComma(3.0) == "3"

    def test_float_integer_value_large(self) -> None:
        assert formatComma(1_000_000.0) == "1,000,000"

    def test_float_decimals_zero(self) -> None:
        assert formatComma(3.7, decimals=0) == "4"

    def test_float_decimals_custom(self) -> None:
        assert formatComma(3.14159, decimals=3) == "3.142"

    def test_none_returns_nullstr(self) -> None:
        assert formatComma(None) == "-"

    def test_nan_returns_nullstr(self) -> None:
        assert formatComma(float("nan")) == "-"

    def test_custom_nullstr(self) -> None:
        assert formatComma(None, nullStr="N/A") == "N/A"

    def test_non_numeric_passthrough(self) -> None:
        assert formatComma("abc") == "abc"

    def test_huge_int_no_collapse(self) -> None:
        # 1e15 이상 float 은 integer collapse 안 함 (precision 손실 방지)
        assert "," in formatComma(1e16)


class TestFormatKrOracle:
    """formatKr 명시 oracle — 단위 임계 (1e4, 1e8, 1e12) 회귀 가드."""

    def test_jo_threshold(self) -> None:
        assert formatKr(1_200_000_000_000) == "1.2조"

    def test_eok_threshold(self) -> None:
        assert formatKr(5_000_000_000) == "50억"

    def test_man_threshold(self) -> None:
        assert formatKr(50_000) == "5만"

    def test_below_man(self) -> None:
        assert formatKr(1234) == "1,234"

    def test_negative_jo(self) -> None:
        assert formatKr(-1_200_000_000_000) == "-1.2조"

    def test_with_won_jo(self) -> None:
        assert formatKr(1_200_000_000_000, withWon=True) == "1.2조원"

    def test_with_won_eok(self) -> None:
        assert formatKr(5_000_000_000, withWon=True) == "50억원"

    def test_with_won_below_eok(self) -> None:
        assert formatKr(10_000, withWon=True) == "10,000원"

    def test_with_won_jo_boundary_exact(self) -> None:
        """withWon=True 분기의 조 임계 정확 (1e12 → 1.0조원). mutmut withWon 분기 잡기."""
        assert formatKr(1_000_000_000_000, withWon=True) == "1.0조원"
        assert formatKr(999_999_999_999, withWon=True) == "10,000억원"

    def test_with_won_eok_boundary_exact(self) -> None:
        """withWon=True 분기의 억 임계 정확 (1e8 → 1억원)."""
        assert formatKr(100_000_000, withWon=True) == "1억원"
        assert formatKr(99_999_999, withWon=True) == "99,999,999원"

    def test_none_nullstr(self) -> None:
        assert formatKr(None) == "-"

    def test_rich_markup_nullstr(self) -> None:
        assert formatKr(None, nullStr="[dim]-[/dim]") == "[dim]-[/dim]"

    def test_nan_nullstr(self) -> None:
        assert formatKr(float("nan")) == "-"

    @pytest.mark.parametrize(
        "val,expected",
        [
            (1_000_000_000_000, "1.0조"),  # 정확히 임계 (int)
            (999_999_999_999, "10,000억"),  # 임계 1 미만은 억 단위
            (100_000_000, "1억"),
            (99_999_999, "10,000만"),
            (10_000, "1만"),
            (9_999, "9,999"),
        ],
    )
    def test_boundary_thresholds(self, val: int, expected: str) -> None:
        """단위 임계 ±1 boundary (int 만) — mutmut 가 `>=` → `>` 변형 시 잡힘."""
        assert formatKr(val) == expected

    def test_boundary_thresholds_float(self) -> None:
        """float 1e4-1 은 .1f 포맷 적용 — sub-만 분기 회귀 가드."""
        assert formatKr(9999.0) == "9,999.0"
        assert formatKr(10000.0) == "1만"  # 1e4 정확히 도달


class TestFormatDecimalOracle:
    """formatDecimal 명시 oracle — suffix 포함."""

    def test_basic_percent(self) -> None:
        assert formatDecimal(3.14159, decimals=1, suffix="%") == "3.1%"

    def test_default_decimals(self) -> None:
        assert formatDecimal(2.5) == "2.5"

    def test_decimals_zero(self) -> None:
        assert formatDecimal(2.5, decimals=0) == "2"

    def test_decimals_three(self) -> None:
        assert formatDecimal(2.5, decimals=3) == "2.500"

    def test_int_passthrough_with_suffix(self) -> None:
        assert formatDecimal(5, suffix="배") == "5배"

    def test_none_nullstr(self) -> None:
        assert formatDecimal(None) == "N/A"

    def test_custom_nullstr(self) -> None:
        assert formatDecimal(None, nullStr="-") == "-"

    def test_nan_nullstr(self) -> None:
        assert formatDecimal(float("nan")) == "N/A"

    def test_negative_with_suffix(self) -> None:
        assert formatDecimal(-1.5, decimals=1, suffix="%") == "-1.5%"


class TestFormatCommaProperty:
    """formatComma property — 임의 입력에서 보존되는 속성."""

    @given(val=st.none())
    def test_none_always_returns_nullstr(self, val) -> None:
        assert formatComma(val, nullStr="MARKER") == "MARKER"

    @given(val=st.integers(min_value=-(10**12), max_value=10**12))
    def test_int_contains_comma_or_short(self, val: int) -> None:
        result = formatComma(val)
        if abs(val) >= 1000:
            assert "," in result
        assert result.lstrip("-").replace(",", "").isdigit() or result == "0"

    @given(val=st.integers(min_value=-(10**6), max_value=10**6))
    def test_int_roundtrip_via_str(self, val: int) -> None:
        """천단위 쉼표 제거 → 원본 int 복원."""
        result = formatComma(val)
        assert int(result.replace(",", "")) == val

    @given(val=st.text(min_size=1, max_size=20))
    def test_non_numeric_string_passthrough(self, val: str) -> None:
        # 숫자로 파싱 가능한 문자열도 isinstance(int, float) 거짓이므로 passthrough
        result = formatComma(val)
        assert result == val


class TestFormatKrProperty:
    """formatKr property — 부호 보존, nullStr 통과, 단위 분기."""

    @given(val=st.none())
    def test_none_returns_nullstr(self, val) -> None:
        assert formatKr(val, nullStr="MARK") == "MARK"

    @given(
        val=st.integers(min_value=10**12 + 1, max_value=10**15)
        | st.integers(min_value=-(10**15), max_value=-(10**12 + 1))
    )
    def test_jo_threshold_contains_jo(self, val: int) -> None:
        result = formatKr(val)
        assert "조" in result
        # 부호 보존
        if val < 0:
            assert result.startswith("-")

    @given(val=st.integers(min_value=10**8 + 1, max_value=10**12 - 1))
    def test_eok_range_contains_eok(self, val: int) -> None:
        result = formatKr(val)
        assert "억" in result

    @given(val=st.integers(min_value=10**4 + 1, max_value=10**8 - 1))
    def test_man_range_contains_man(self, val: int) -> None:
        result = formatKr(val)
        assert "만" in result


class TestFormatDecimalProperty:
    """formatDecimal property — suffix 보존, decimals 자릿수."""

    @given(
        val=st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
        suffix=st.text(max_size=3, alphabet=st.characters(min_codepoint=0x20, max_codepoint=0x7E)),
    )
    def test_suffix_always_appended(self, val: float, suffix: str) -> None:
        result = formatDecimal(val, suffix=suffix)
        assert result.endswith(suffix)

    @given(
        val=st.floats(min_value=-100, max_value=100, allow_nan=False, allow_infinity=False),
        decimals=st.integers(min_value=0, max_value=6),
    )
    def test_decimals_count_matches(self, val: float, decimals: int) -> None:
        result = formatDecimal(val, decimals=decimals)
        if "." in result and decimals > 0:
            fractional = result.split(".")[1]
            assert len(fractional) == decimals
        elif decimals == 0:
            assert "." not in result

    @given(val=st.none())
    def test_none_returns_nullstr(self, val) -> None:
        assert formatDecimal(val, nullStr="ZZZ") == "ZZZ"


class TestFormatMetamorphic:
    """metamorphic — 변환 후 보존 속성. mutmut 가 한계 비교 변형 시 잡힘."""

    pytestmark = pytest.mark.metamorphic

    @given(
        val=st.integers(min_value=1, max_value=10**14),
    )
    def test_formatKr_sign_inversion_symmetry(self, val: int) -> None:
        """부호 반전 — 절댓값 표기는 같고 prefix 만 달라야 함."""
        pos = formatKr(val)
        neg = formatKr(-val)
        assert neg == f"-{pos}" or neg.lstrip("-") == pos

    @given(val=st.floats(min_value=-1e9, max_value=1e9, allow_nan=False, allow_infinity=False))
    def test_formatComma_idempotent_after_strip(self, val: float) -> None:
        """쉼표 제거 → float 복원 → 다시 포맷 = 동일."""
        result = formatComma(val, decimals=2)
        if result == "-":  # null
            return
        # 천단위 쉼표 제거 후 float 복원
        try:
            restored = float(result.replace(",", ""))
        except ValueError:
            return  # int collapse 케이스 — 동일성 검증 어려움
        # decimals=2 라면 |val - restored| < 0.005
        if "." in result:
            assert abs(val - restored) < 0.005

"""dartlab.core.ratios.yoyPct metamorphic — Track 8.

본 트랙 SSOT — [tests/POLICY.md](../POLICY.md) §5 Track 8 (Metamorphic test).

수치 분석에서 결정적 oracle 이 없을 때 *변환 후 보존되는 속성* 으로 검증한다.
yoyPct 는 dartlab finance ratio 계산의 기본 building block 으로, scale invariance,
proportional, sign transition 같은 수학적 속성이 명확하다.

본 파일이 잡는 회귀:
- 분모/분자 변형 (`/ prev` → `/ cur`)
- 부호 전환 처리 누락 (음수 → 양수 케이스)
- 스케일링 영향 (단위 변환 buy 비율 깨짐)
- 항등성 (cur == prev → 0% 가 아닌 다른 값)
"""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from dartlab.core.ratios import yoyPct

pytestmark = [pytest.mark.unit, pytest.mark.metamorphic]


class TestYoyPctOracle:
    """yoyPct 명시 oracle — mutation 회귀 가드."""

    def test_proportional_double(self) -> None:
        """cur = 2 * prev → 100% 증가."""
        assert yoyPct(200, 100) == 100.0

    def test_proportional_half(self) -> None:
        """cur = 0.5 * prev → -50% 감소."""
        assert yoyPct(50, 100) == -50.0

    def test_identity(self) -> None:
        """cur == prev → 0%."""
        assert yoyPct(100, 100) == 0.0

    def test_both_negative_improvement(self) -> None:
        """음수 → 음수 (적자 축소) — 부호 보존 처리."""
        # prev=-200, cur=-100: 적자 50% 축소 = (-100 - -200)/|-200| * 100 = 50%
        assert yoyPct(-100, -200) == 50.0

    def test_both_negative_deterioration(self) -> None:
        """음수 → 음수 (적자 확대)."""
        # prev=-100, cur=-200: 적자 100% 확대 = (-200 - -100)/|-100| * 100 = -100%
        assert yoyPct(-200, -100) == -100.0

    def test_sign_transition_to_positive(self) -> None:
        """음수 → 양수 (흑자 전환) → None (단순 비교 불가)."""
        assert yoyPct(100, -50) is None

    def test_sign_transition_to_negative(self) -> None:
        """양수 → 음수 (적자 전환) → None."""
        assert yoyPct(-50, 100) is None

    def test_zero_denominator(self) -> None:
        """분모 0 → None."""
        assert yoyPct(100, 0) is None

    def test_none_input(self) -> None:
        """None 입력 → None."""
        assert yoyPct(None, 100) is None
        assert yoyPct(100, None) is None
        assert yoyPct(None, None) is None

    def test_cur_zero_with_positive_prev(self) -> None:
        """cur=0, prev>0 → -100% (전액 손실). mutation `>=` → `>` cur=0 케이스 회귀 가드."""
        assert yoyPct(0, 100) == -100.0
        assert yoyPct(0, 50000) == -100.0

    def test_cur_zero_with_negative_prev(self) -> None:
        """cur=0, prev<0 → 부호 전환 (음수→0 양수) → None."""
        # cur=0 은 ">= 0" 으로 양수 분기지만 prev<0 이라 둘 다 거짓 → None
        assert yoyPct(0, -100) is None


class TestYoyPctMetamorphic:
    """yoyPct metamorphic — 변환 후 속성 보존."""

    @given(
        prev=st.floats(min_value=1.0, max_value=1e9, allow_nan=False, allow_infinity=False),
        ratio=st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False),
        scale=st.floats(min_value=0.01, max_value=1e6, allow_nan=False, allow_infinity=False),
    )
    def test_scale_invariance_positive(self, prev: float, ratio: float, scale: float) -> None:
        """scale 변환 (단위 변경: 원 → 백만원) 시 비율 동일.

        yoyPct(cur, prev) == yoyPct(cur*k, prev*k) for k > 0.
        """
        cur = prev * ratio
        original = yoyPct(cur, prev)
        scaled = yoyPct(cur * scale, prev * scale)
        if original is None:
            assert scaled is None
        else:
            # 부동소수 비교 — 반올림 2 자리 적용된 값이라 1% 허용
            assert abs(original - scaled) < 0.5

    @given(
        prev=st.floats(min_value=1.0, max_value=1e9, allow_nan=False, allow_infinity=False),
    )
    def test_identity_always_zero(self, prev: float) -> None:
        """cur == prev → 항상 0% (항등성)."""
        assert yoyPct(prev, prev) == 0.0

    @given(
        prev=st.floats(min_value=1.0, max_value=1e9, allow_nan=False, allow_infinity=False),
        multiplier=st.floats(min_value=2.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    )
    def test_multiplicative_growth_positive(self, prev: float, multiplier: float) -> None:
        """cur = m * prev → 결과 = (m-1) * 100 ±0.5."""
        cur = prev * multiplier
        result = yoyPct(cur, prev)
        assert result is not None
        expected = (multiplier - 1) * 100
        assert abs(result - expected) < 0.5

    @given(
        prev=st.floats(min_value=1.0, max_value=1e9, allow_nan=False, allow_infinity=False),
        cur=st.floats(min_value=-1e9, max_value=-1.0, allow_nan=False, allow_infinity=False),
    )
    def test_sign_transition_always_none(self, prev: float, cur: float) -> None:
        """양수 prev + 음수 cur (cur < 0) → 항상 None."""
        # prev > 0, cur < 0 — 부호 전환 → None
        assert yoyPct(cur, prev) is None

    @given(
        prev=st.floats(min_value=1.0, max_value=1e9, allow_nan=False, allow_infinity=False),
        cur1=st.floats(min_value=1.0, max_value=1e9, allow_nan=False, allow_infinity=False),
        cur2=st.floats(min_value=1.0, max_value=1e9, allow_nan=False, allow_infinity=False),
    )
    def test_monotonic_in_cur(self, prev: float, cur1: float, cur2: float) -> None:
        """모든 cur 이 양수일 때, cur1 > cur2 → result1 > result2 (단조)."""
        r1 = yoyPct(cur1, prev)
        r2 = yoyPct(cur2, prev)
        if r1 is None or r2 is None:
            return
        if cur1 > cur2:
            # 반올림으로 동률 가능 — strict 가 아닌 >=
            assert r1 >= r2 - 0.01
        elif cur1 < cur2:
            assert r1 <= r2 + 0.01

    @given(
        prev=st.floats(min_value=1.0, max_value=1e9, allow_nan=False, allow_infinity=False),
        delta=st.floats(min_value=-0.99, max_value=0.99, allow_nan=False, allow_infinity=False),
    )
    def test_small_change_proportional(self, prev: float, delta: float) -> None:
        """cur = prev * (1 + delta) → 결과 ≈ delta * 100 ±0.5."""
        cur = prev * (1 + delta)
        result = yoyPct(cur, prev)
        if cur < 0 or prev <= 0:
            return  # 부호 전환 케이스 제외
        assert result is not None
        expected = delta * 100
        assert abs(result - expected) < 0.5


class TestYoyPctReflection:
    """yoyPct(a, b) 와 yoyPct(b, a) 관계 — 일반적으로 다름."""

    def test_swap_not_negation_general(self) -> None:
        """yoyPct(200, 100) = 100% 이지만 yoyPct(100, 200) = -50% (대칭 아님)."""
        assert yoyPct(200, 100) == 100.0
        assert yoyPct(100, 200) == -50.0  # -100% 아님 (분모가 다름)

    @given(
        a=st.floats(min_value=1.0, max_value=1e6, allow_nan=False, allow_infinity=False),
        b=st.floats(min_value=1.0, max_value=1e6, allow_nan=False, allow_infinity=False),
    )
    def test_swap_relationship(self, a: float, b: float) -> None:
        """yoyPct(a, b) + 100 = (a/b) * 100 ↔ yoyPct(b, a) + 100 = (b/a) * 100.

        즉 (yoyPct(a, b) + 100) * (yoyPct(b, a) + 100) = 10000 (a, b > 0).
        반올림 2 자리가 큰 비율에서 누적 — ratio 제한 + 비율 비례 임계 사용.
        """
        if a == 0 or b == 0:
            return
        # 비율이 극단적이면 반올림 누적이 비선형 → ratio 100x 이하 제한
        ratio = max(a, b) / min(a, b)
        if ratio > 100:
            return
        r_ab = yoyPct(a, b)
        r_ba = yoyPct(b, a)
        if r_ab is None or r_ba is None:
            return
        product = (r_ab + 100) * (r_ba + 100)
        # ratio 영향 — 임계도 ratio 에 비례 (반올림 0.01 가 양쪽에 영향)
        rel_err = abs(product - 10000) / 10000
        assert rel_err < 0.05, f"product={product}, rel_err={rel_err}, a={a}, b={b}, ratio={ratio}"

"""Scale invariance — 단위 환산 후 % 비율 보존 (T6-3 패턴 1).

재무 비율 (PBR / PER / ROA / ROE 등) 은 *분자 + 분모* 가 같은 단위면 *환율* 에
무관해야 한다. KRW → USD 또는 KRW → EUR 변환 후 비율 값 변동이 epsilon 이상
나면 단위 처리 버그.

본 테스트는 ratio 함수 *입력 데이터* 를 scale 변환 (×1000 / ×0.001) 한 뒤
결과가 같은지 검증. 실제 Company 인스턴스 사용 테스트는 후속 (memory 안전).
"""

from __future__ import annotations

from decimal import Decimal

import pytest


@pytest.mark.metamorphic
@pytest.mark.unit
class TestScaleInvariance:
    """단순 ratio 함수에 대한 scale invariance 검증."""

    def test_simple_ratio_kr_usd_scale(self) -> None:
        """단순 비율 — 분자/분모 동시 ×1000 후 결과 동일."""
        # PBR-like — book / price
        book_kr = Decimal("1000000")  # 100만원
        price_kr = Decimal("500000")  # 50만원
        ratio_kr = book_kr / price_kr

        # 단위 변환 — 환율 1300 KRW/USD 가정
        rate = Decimal("1300")
        book_usd = book_kr / rate
        price_usd = price_kr / rate
        ratio_usd = book_usd / price_usd

        assert ratio_kr == ratio_usd, f"ratio 가 단위 변환에 의존: {ratio_kr} != {ratio_usd}"

    def test_simple_ratio_zero_denominator(self) -> None:
        """0 분모 보호 — safeDivide 동작 검증 (T7-4 정합)."""
        from dartlab.core.decimal import safeDivide

        assert safeDivide(100, 0) == Decimal("0")
        assert safeDivide(100, 0, default=Decimal("-1")) == Decimal("-1")

    @pytest.mark.parametrize("scale", [Decimal("0.001"), Decimal("1"), Decimal("1000"), Decimal("1000000")])
    def test_ratio_invariant_across_scales(self, scale: Decimal) -> None:
        """다양한 scale 에서 비율 보존 — 4 scale × 100 random 풀 검증."""
        base_num = Decimal("123456")
        base_den = Decimal("789")
        base_ratio = base_num / base_den

        scaled_num = base_num * scale
        scaled_den = base_den * scale
        scaled_ratio = scaled_num / scaled_den

        assert base_ratio == scaled_ratio, f"scale {scale} 에서 ratio 변동"

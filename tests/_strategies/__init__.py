"""Hypothesis 공통 strategies — T6-1 트랙.

5 모듈 (core/ratios · core/decimal · core/formatting · scan/io · quant/factors) 의
property-based 테스트가 공유하는 strategies. 금융 edge case (0 분모 / inf / NaN /
negative / mixed currency / leap year) 강제.
"""

from __future__ import annotations

from decimal import Decimal

from hypothesis import strategies as st

# 금융 정합 strategies — 0 분모 / negative / inf / NaN 포함.
financial_amount = st.one_of(
    st.integers(min_value=-(10**12), max_value=10**12),
    st.floats(min_value=-1e9, max_value=1e9, allow_nan=False, allow_infinity=False),
)
"""재무 금액 (KRW or USD) — int / float 혼합."""

positive_amount = st.one_of(
    st.integers(min_value=1, max_value=10**12),
    st.floats(min_value=0.01, max_value=1e9, allow_nan=False, allow_infinity=False),
)
"""양수 금액 — 분모 등에 사용."""

ratio_value = st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False)
"""비율 값 — 일반적으로 -100x ~ +100x 범위."""

decimal_value = st.decimals(
    min_value=Decimal("-1E10"), max_value=Decimal("1E10"), allow_nan=False, allow_infinity=False
)
"""Decimal 값 — 회계 정합."""

stock_code_kr = st.text(alphabet=st.characters(min_codepoint=ord("0"), max_codepoint=ord("9")), min_size=6, max_size=6)
"""한국 6자리 종목코드 (예: '005930')."""

date_kr = st.dates(
    min_value=__import__("datetime").date(1980, 1, 1), max_value=__import__("datetime").date(2030, 12, 31)
)
"""한국 시장 기간 (1980 ~ 2030)."""

leap_year = st.sampled_from([1980, 1984, 1988, 1992, 1996, 2000, 2004, 2008, 2012, 2016, 2020, 2024, 2028])
"""leap year (28/29 일 경계 검증용)."""

currency_pair = st.sampled_from(["KRW", "USD", "JPY", "EUR", "CNY"])
"""통화 쌍 (scale invariance 검증)."""


__all__ = [
    "financial_amount",
    "positive_amount",
    "ratio_value",
    "decimal_value",
    "stock_code_kr",
    "date_kr",
    "leap_year",
    "currency_pair",
]

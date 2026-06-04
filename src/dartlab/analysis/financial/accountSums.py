"""재무 계정 합산 헬퍼 — snake_id 기반 finance dict 의 차입금/매출원가/판관비/법인세.

`Company.panel("BS")` 같은 finance dict 에서 분리 키 (예: ``shortterm_borrowings``,
``longterm_borrowings``) 우선 합산하고, 모두 결손이면 통합 키 (``borrowings``)
fallback 한다. analysis/credit 엔진의 차입금·비용 분석이 공유.
"""

from __future__ import annotations

_BORROWING_KEYS = (
    "shortterm_borrowings",
    "longterm_borrowings",
    "noncurrent_borrowings",
    "current_portion_of_longterm_borrowings",
    "borrowings",
)
_BOND_KEYS = ("debentures", "bonds_payable", "current_portion_of_debentures")

_COGS_KEYS = (
    "cost_of_sales",
    "cost_of_goods_sold",
    "product_cost_of_sales",
    "merchandise_cost_of_sales",
    "construction_cost_of_sales",
    "service_cost_of_sales",
)

_SGA_KEYS = (
    "selling_and_administrative_expenses",
    "selling_expenses",
    "administrative_expenses",
    "sga",
)

_INCOME_TAX_KEYS = (
    "income_taxes",
    "income_tax_expense",
    "current_income_tax_expense",
    "deferred_income_tax_expense",
)


def _sumWithFallback(snakeData: dict, col: str, separateKeys: tuple, fallbackKey: str) -> float:
    """분리 키 우선 합산, 모두 결손이면 통합 키 fallback."""
    parts = []
    for sid in separateKeys:
        if sid == fallbackKey:
            continue
        v = snakeData.get(sid, {}).get(col)
        if v is not None and v != 0:
            parts.append(v)
    if not parts:
        v = snakeData.get(fallbackKey, {}).get(col)
        if v is not None:
            parts.append(v)
    return sum(parts)


def sumBorrowings(snakeData: dict, col: str) -> float:
    """차입금 합산 — snakeId 키 dict용. Phase 4 G12.4: K-IFRS 리스부채 포함 (Damodaran IC).

    Capabilities:
        - _BORROWING_KEYS 우선 + borrowings fallback + 사채 + 리스부채 합산
        - Damodaran IC = Equity + Debt (lease 포함) - Cash 표준

    Args:
        snakeData: snakeId 키 dict (BS).
        col: 기간 컬럼 명.

    Returns:
        float — 합산 차입금 (원).

    Guide:
        리스부채 포함은 K-IFRS 표준 (Damodaran IC). 미포함 시 부채 underestimate.

    When:
        WACC + 부채 계산 + AI 차입금 답변.

    How:
        snakeId 우선순위 순회 → 사채 + lease 추가.

    Requires:
        snakeData BS dict.

    Raises:
        없음.

    Example:
        >>> sumBorrowings(bs, "2024")
        150000000000

    See Also:
        - sumBorrowingsKorean : 한국어 키 버전
        - capital.py : 자본 구성

    AIContext:
        "차입금 총액" 답변 시 사용.
    """
    parts = []
    for sid in _BORROWING_KEYS:
        if sid == "borrowings":
            continue
        v = snakeData.get(sid, {}).get(col)
        if v is not None and v != 0:
            parts.append(v)
    if not parts:
        v = snakeData.get("borrowings", {}).get(col)
        if v is not None:
            parts.append(v)
    for sid in _BOND_KEYS:
        v = snakeData.get(sid, {}).get(col)
        if v is not None and v != 0:
            parts.append(v)
    # Phase 4 G12.4: 리스부채 추가 — Damodaran IC = Equity + Debt (incl. lease) - Cash
    for sid in ("lease_liabilities", "operating_lease_obligations", "current_portion_of_finance_leases"):
        v = snakeData.get(sid, {}).get(col)
        if v is not None and v != 0:
            parts.append(v)
    return sum(parts)


def sumCostOfSales(snakeData: dict, col: str) -> float:
    """매출원가 합산.

    Requires:
        snakeData IS dict + _COGS_KEYS.

    Raises:
        없음.

    Example:
        >>> sumCostOfSales(is_data, "2024")
        80000000000
    """
    return _sumWithFallback(snakeData, col, _COGS_KEYS, "cost_of_sales")


def sumSGA(snakeData: dict, col: str) -> float:
    """판매관리비 합산.

    Requires:
        snakeData IS dict + _SGA_KEYS.

    Raises:
        없음.

    Example:
        >>> sumSGA(is_data, "2024")
        12000000000
    """
    return _sumWithFallback(snakeData, col, _SGA_KEYS, "selling_and_administrative_expenses")


def sumIncomeTax(snakeData: dict, col: str) -> float:
    """법인세 합산.

    Requires:
        snakeData IS dict + _INCOME_TAX_KEYS.

    Raises:
        없음.

    Example:
        >>> sumIncomeTax(is_data, "2024")
        3000000000
    """
    return _sumWithFallback(snakeData, col, _INCOME_TAX_KEYS, "income_taxes")


_KR_BORROWING_SHORT = ("단기차입금", "차입금단기", "short_term_borrowings")
_KR_BORROWING_LONG = ("장기차입금", "long_term_borrowings")
_KR_BORROWING_UNIFIED = ("차입부채", "차입금", "장기차입부채", "유동성장기차입금")


def sumBorrowingsKorean(bsData: dict, col: str) -> tuple[float, float, float]:
    """한국어 키 BS dict의 차입금 합산.

    Returns:
        (stBorrow, ltBorrow, totalBorrowing)

    Capabilities:
        - 한국어 키 (단기차입금/장기차입금/사채/통합 차입부채) 우선순위 매칭
        - 단/장기 분리 + 합계 반환

    Args:
        bsData: 한국어 키 BS dict.
        col: 기간 컬럼.

    Guide:
        한국어 BS 처리. snakeId 표준 사용 가능하면 sumBorrowings 우선.

    When:
        한국어 BS dict 처리 + AI 한국어 회계 답변.

    How:
        _KR_BORROWING_SHORT/LONG/UNIFIED 순회 → 합계.

    Requires:
        한국어 키 BS dict.

    Raises:
        없음.

    Example:
        >>> sumBorrowingsKorean(bs, "2024")
        (50000000000, 100000000000, 150000000000)

    See Also:
        - sumBorrowings : snakeId 버전

    AIContext:
        한국어 BS 처리 invisible helper.
    """
    stb = 0.0
    for k in _KR_BORROWING_SHORT:
        v = bsData.get(k, {}).get(col)
        if v is not None:
            stb = float(v)
            break
    ltb = 0.0
    for k in _KR_BORROWING_LONG:
        v = bsData.get(k, {}).get(col)
        if v is not None:
            ltb = float(v)
            break
    if stb == 0 and ltb == 0:
        for k in _KR_BORROWING_UNIFIED:
            v = bsData.get(k, {}).get(col)
            if v is not None:
                stb = float(v)
                break
    bondsVal = bsData.get("사채", {}).get(col) or 0
    total = stb + ltb + float(bondsVal)
    return stb, ltb, total

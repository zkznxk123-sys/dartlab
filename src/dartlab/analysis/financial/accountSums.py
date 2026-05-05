"""재무 계정 합산 헬퍼 — snake_id 기반 finance dict 의 차입금/매출원가/판관비/법인세.

`Company.show("BS")` 같은 finance dict 에서 분리 키 (예: ``shortterm_borrowings``,
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
    """차입금 합산 — snakeId 키 dict용. Phase 4 G12.4: K-IFRS 리스부채 포함 (Damodaran IC)."""
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
    """매출원가 합산."""
    return _sumWithFallback(snakeData, col, _COGS_KEYS, "cost_of_sales")


def sumSGA(snakeData: dict, col: str) -> float:
    """판매관리비 합산."""
    return _sumWithFallback(snakeData, col, _SGA_KEYS, "selling_and_administrative_expenses")


def sumIncomeTax(snakeData: dict, col: str) -> float:
    """법인세 합산."""
    return _sumWithFallback(snakeData, col, _INCOME_TAX_KEYS, "income_taxes")


_KR_BORROWING_SHORT = ("단기차입금", "차입금단기", "short_term_borrowings")
_KR_BORROWING_LONG = ("장기차입금", "long_term_borrowings")
_KR_BORROWING_UNIFIED = ("차입부채", "차입금", "장기차입부채", "유동성장기차입금")


def sumBorrowingsKorean(bsData: dict, col: str) -> tuple[float, float, float]:
    """한국어 키 BS dict의 차입금 합산.

    Returns:
        (stBorrow, ltBorrow, totalBorrowing)
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

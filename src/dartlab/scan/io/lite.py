"""finance-lite scan prebuild specification."""

from __future__ import annotations

# 원본 `finance.parquet`(307MB) 을 아래 30 개 snakeId 로 필터하고 2022년부터만
# 남긴 경량본. 브라우저 pyodide 에서 `pl.scan_parquet` 미지원이라 pyarrow 로 전체 로드한다.

_LITE_ACCOUNTS_IS: tuple[str, ...] = (
    "sales",
    "cost_of_sales",
    "gross_profit",
    "operating_expenses",
    "operating_profit",
    "finance_income",
    "finance_costs",
    "profit_before_tax",
    "income_tax_expense",
    "net_income",
)
_LITE_ACCOUNTS_BS: tuple[str, ...] = (
    "cash_and_cash_equivalents",
    "current_assets",
    "inventories",
    "trade_receivables",
    "noncurrent_assets",
    "property_plant_and_equipment",
    "intangible_assets",
    "current_liabilities",
    "trade_payables",
    "noncurrent_liabilities",
    "total_stockholders_equity",
    "retained_earnings",
)
_LITE_ACCOUNTS_CF: tuple[str, ...] = (
    "operating_cashflow",
    "investing_cashflow",
    "financing_cashflow",
    "cash_and_cash_equivalents_at_the_end_of_year",
    "cash_and_cash_equivalents_beginning",
    "changes_in_operating_assets_and_liabilities",
    "depreciation",
    "net_increase_decrease_in_cash_and_cash_equivalents",
)
LITE_ACCOUNTS: tuple[str, ...] = _LITE_ACCOUNTS_IS + _LITE_ACCOUNTS_BS + _LITE_ACCOUNTS_CF

# lite 빌드에 포함할 재무제표 구분 (SCE 제외 — 용량 27.8% 차지, scan 미사용)
LITE_SJ_DIVS: tuple[str, ...] = ("IS", "BS", "CIS", "CF")

# lite 기본 시작 연도 (5년치 분기 보장: 2022Q1 ~ 최신)
LITE_SINCE_YEAR: int = 2022

__all__ = [
    "LITE_ACCOUNTS",
    "LITE_SINCE_YEAR",
    "LITE_SJ_DIVS",
    "_LITE_ACCOUNTS_BS",
    "_LITE_ACCOUNTS_CF",
    "_LITE_ACCOUNTS_IS",
]

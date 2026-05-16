"""K-IFRS 표준 항목 28 종 + 시리즈 추출.

회사마다 account_nm 이 다름 (카카오 "영업수익" vs 삼성 "매출액").
IFRS taxonomy account_id 우선 + account_nm 키워드 fallback.

Returns 형식 통일: extractSeries 는 list[float|None] 반환 (periods 길이 일치).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import polars as pl


@dataclass(frozen=True)
class StandardAccount:
    """표준 재무 항목."""

    key: str
    label: str
    sjDiv: str  # "IS" | "BS" | "CF"
    ifrsIds: tuple[str, ...]
    nameKeywords: tuple[str, ...]


_STANDARDS: tuple[StandardAccount, ...] = (
    # ─── IS 10 ───
    StandardAccount(
        "revenue", "매출액", "IS", ("ifrs-full_Revenue", "ifrs_Revenue"), ("매출액", "영업수익", "수익(매출액)", "매출")
    ),
    StandardAccount("costOfSales", "매출원가", "IS", ("ifrs-full_CostOfSales", "ifrs_CostOfSales"), ("매출원가",)),
    StandardAccount("grossProfit", "매출총이익", "IS", (), ("매출총이익",)),
    StandardAccount(
        "operatingIncome",
        "영업이익",
        "IS",
        ("dart_OperatingIncomeLoss", "ifrs-full_ProfitLossFromOperatingActivities", "ifrs_OperatingProfitLoss"),
        ("영업이익", "영업이익(손실)"),
    ),
    StandardAccount(
        "netIncome",
        "당기순이익",
        "IS",
        ("ifrs-full_ProfitLoss", "ifrs_ProfitLoss"),
        ("당기순이익", "당기순이익(손실)", "순이익"),
    ),
    StandardAccount(
        "sga",
        "판매비와관리비",
        "IS",
        ("dart_TotalSellingGeneralAdministrativeExpenses", "ifrs-full_SellingGeneralAndAdministrativeExpense"),
        ("판매비와관리비", "판매관리비"),
    ),
    StandardAccount("rnd", "연구개발비", "IS", ("dart_ResearchAndDevelopmentExpenses",), ("연구개발",)),
    StandardAccount(
        "financeIncome", "금융수익", "IS", ("ifrs-full_FinanceIncome", "ifrs_FinanceIncome"), ("금융수익",)
    ),
    StandardAccount("financeCosts", "금융비용", "IS", ("ifrs-full_FinanceCosts", "ifrs_FinanceCosts"), ("금융비용",)),
    StandardAccount(
        "incomeTax",
        "법인세비용",
        "IS",
        ("ifrs-full_IncomeTaxExpenseContinuingOperations", "ifrs_IncomeTaxExpense"),
        ("법인세비용",),
    ),
    # ─── BS 14 ───
    StandardAccount("assets", "자산총계", "BS", ("ifrs-full_Assets", "ifrs_Assets"), ("자산총계",)),
    StandardAccount(
        "currentAssets", "유동자산", "BS", ("ifrs-full_CurrentAssets", "ifrs_CurrentAssets"), ("유동자산",)
    ),
    StandardAccount(
        "nonCurrentAssets", "비유동자산", "BS", ("ifrs-full_NoncurrentAssets", "ifrs_NoncurrentAssets"), ("비유동자산",)
    ),
    StandardAccount(
        "cash",
        "현금및현금성자산",
        "BS",
        ("ifrs-full_CashAndCashEquivalents", "ifrs_CashAndCashEquivalents"),
        ("현금및현금성자산", "현금성자산"),
    ),
    StandardAccount("inventories", "재고자산", "BS", ("ifrs-full_Inventories", "ifrs_Inventories"), ("재고자산",)),
    StandardAccount(
        "receivables",
        "매출채권",
        "BS",
        ("ifrs-full_TradeAndOtherCurrentReceivables", "dart_ShortTermTradeReceivable"),
        ("매출채권",),
    ),
    StandardAccount("liabilities", "부채총계", "BS", ("ifrs-full_Liabilities", "ifrs_Liabilities"), ("부채총계",)),
    StandardAccount(
        "currentLiabilities",
        "유동부채",
        "BS",
        ("ifrs-full_CurrentLiabilities", "ifrs_CurrentLiabilities"),
        ("유동부채",),
    ),
    StandardAccount(
        "nonCurrentLiabilities",
        "비유동부채",
        "BS",
        ("ifrs-full_NoncurrentLiabilities", "ifrs_NoncurrentLiabilities"),
        ("비유동부채",),
    ),
    StandardAccount(
        "payables",
        "매입채무",
        "BS",
        ("ifrs-full_TradeAndOtherCurrentPayables", "dart_ShortTermTradePayables"),
        ("매입채무",),
    ),
    StandardAccount(
        "shortDebt", "단기차입금", "BS", ("ifrs-full_ShorttermBorrowings", "ifrs_ShorttermBorrowings"), ("단기차입금",)
    ),
    StandardAccount(
        "longDebt",
        "장기차입금",
        "BS",
        ("ifrs-full_LongtermBorrowings", "ifrs_LongtermBorrowings"),
        ("장기차입금", "사채"),
    ),
    StandardAccount("equity", "자본총계", "BS", ("ifrs-full_Equity", "ifrs_Equity"), ("자본총계",)),
    StandardAccount(
        "retainedEarnings", "이익잉여금", "BS", ("ifrs-full_RetainedEarnings", "ifrs_RetainedEarnings"), ("이익잉여금",)
    ),
    # ─── CF 4 ───
    StandardAccount(
        "cfOperating",
        "영업활동현금흐름",
        "CF",
        ("ifrs-full_CashFlowsFromUsedInOperatingActivities", "ifrs_CashFlowsFromUsedInOperatingActivities"),
        ("영업활동", "영업활동현금흐름"),
    ),
    StandardAccount(
        "cfInvesting",
        "투자활동현금흐름",
        "CF",
        ("ifrs-full_CashFlowsFromUsedInInvestingActivities", "ifrs_CashFlowsFromUsedInInvestingActivities"),
        ("투자활동", "투자활동현금흐름"),
    ),
    StandardAccount(
        "cfFinancing",
        "재무활동현금흐름",
        "CF",
        ("ifrs-full_CashFlowsFromUsedInFinancingActivities", "ifrs_CashFlowsFromUsedInFinancingActivities"),
        ("재무활동", "재무활동현금흐름"),
    ),
    StandardAccount(
        "capex",
        "유형자산취득",
        "CF",
        (
            "ifrs-full_PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",
            "dart_PurchaseOfPropertyPlantAndEquipment",
        ),
        ("유형자산의취득", "유형자산취득"),
    ),
    StandardAccount(
        "dividendsPaid",
        "배당금지급",
        "CF",
        ("ifrs-full_DividendsPaidClassifiedAsFinancingActivities", "ifrs_DividendsPaid"),
        ("배당금지급",),
    ),
)

_BY_KEY: dict[str, StandardAccount] = {s.key: s for s in _STANDARDS}


def listStandards(sjDiv: str | None = None) -> list[StandardAccount]:
    """표준 항목 카탈로그. sjDiv (BS/IS/CF) 지정 시 해당 영역만."""
    if sjDiv is None:
        return list(_STANDARDS)
    return [s for s in _STANDARDS if s.sjDiv == sjDiv]


def standard(key: str) -> StandardAccount:
    """key 로 표준 항목 1 개 조회."""
    return _BY_KEY[key]


def extractSeries(
    norm: pl.DataFrame,
    key: str,
    periods: Iterable[str],
    *,
    fsDiv: str = "CFS",
) -> list[float | None]:
    """표준 항목 N 기간 값 추출 (list 반환, periods 길이 일치).

    fsDiv: CFS (연결) 우선, 없으면 OFS (별도) fallback.
    accountId IFRS 매칭 우선, 안되면 accountNm 키워드 매칭.
    """
    periods_list = list(periods)
    if norm is None or norm.height == 0:
        return [None] * len(periods_list)
    sa = _BY_KEY.get(key)
    if sa is None:
        return [None] * len(periods_list)

    sub = norm.filter(
        (pl.col("sjDiv") == sa.sjDiv) & (pl.col("fsDiv") == fsDiv) & (pl.col("period").is_in(periods_list))
    )
    if sub.height == 0 and fsDiv == "CFS":
        sub = norm.filter(
            (pl.col("sjDiv") == sa.sjDiv) & (pl.col("fsDiv") == "OFS") & (pl.col("period").is_in(periods_list))
        )
    if sub.height == 0:
        return [None] * len(periods_list)

    idCond = pl.col("accountId").is_in(list(sa.ifrsIds)) if sa.ifrsIds else pl.lit(False)
    nmCond = pl.lit(False)
    for kw in sa.nameKeywords:
        nmCond = nmCond | (pl.col("accountNm").str.strip_chars() == kw)
    cond = idCond | nmCond
    matched = sub.filter(cond)
    if matched.height == 0:
        return [None] * len(periods_list)

    matched = matched.with_columns(pl.when(idCond).then(2).when(nmCond).then(1).otherwise(0).alias("_priority"))
    agg = (
        matched.sort(["_priority", "ord"], descending=[True, False], nulls_last=True)
        .group_by("period")
        .agg(pl.col("amount").first().alias("amount"))
    )
    lookup = dict(zip(agg["period"].to_list(), agg["amount"].to_list(), strict=True))
    return [lookup.get(p) for p in periods_list]

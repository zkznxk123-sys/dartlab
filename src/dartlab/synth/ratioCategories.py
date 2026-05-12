"""재무비율 카테고리 SSOT — analysis · viz · providers 공통 사용.

이전 위치: analysis/financial/ratios.py (line 2029).
새 위치: core — analysis ↔ viz 양방향 cycle 의 한 축. RATIO_CATEGORIES 데이터 자체는
순수 메타 (카테고리명 + 필드명 list) 이라 더 낮은 layer 에 두는 게 자연스럽다.

analysis/financial/ratios.py 는 back-compat 위해 여기서 re-export.
viz/{generators,export/excel} + providers/dart/{_docsIndex,_finance_helpers} +
providers/edgar/company 는 core 에서 직접 import.
"""

from __future__ import annotations

RATIO_CATEGORIES: list[tuple[str, list[str]]] = [
    (
        "profitability",
        [
            "roe",
            "roa",
            "roce",
            "operatingMargin",
            "netMargin",
            "preTaxMargin",
            "grossMargin",
            "ebitdaMargin",
            "costOfSalesRatio",
            "sgaRatio",
            "effectiveTaxRate",
            "incomeQualityRatio",
        ],
    ),
    (
        "stability",
        [
            "debtRatio",
            "currentRatio",
            "quickRatio",
            "cashRatio",
            "equityRatio",
            "interestCoverage",
            "netDebtRatio",
            "noncurrentRatio",
            "workingCapital",
        ],
    ),
    (
        "growth",
        [
            "revenueGrowth",
            "operatingProfitGrowth",
            "netProfitGrowth",
            "assetGrowth",
            "equityGrowthRate",
        ],
    ),
    (
        "efficiency",
        [
            "totalAssetTurnover",
            "fixedAssetTurnover",
            "inventoryTurnover",
            "receivablesTurnover",
            "payablesTurnover",
            "operatingCycle",
        ],
    ),
    (
        "cashflow",
        [
            "fcf",
            "operatingCfMargin",
            "operatingCfToNetIncome",
            "operatingCfToCurrentLiab",
            "capexRatio",
            "dividendPayoutRatio",
            "fcfToOcfRatio",
        ],
    ),
    (
        "composite",
        [
            "roic",
            "dupontMargin",
            "dupontTurnover",
            "dupontLeverage",
            "debtToEbitda",
            "ccc",
            "dso",
            "dio",
            "dpo",
            "piotroskiFScore",
            "altmanZScore",
        ],
    ),
    (
        "absolute",
        [
            "revenue",
            "operatingProfit",
            "netProfit",
            "totalAssets",
            "totalEquity",
            "operatingCashflow",
        ],
    ),
]

"""자본배분 분석 — facade. 본체는 `_capitalAllocationPayout` / `_capitalAllocationReinvest`.

벌어들인 돈을 어디에 쓰는지를 시계열로 추적한다.
"""

from __future__ import annotations

from dartlab.analysis.financial._capitalAllocationPayout import (
    _edgarTreasuryStockFallback,
    calcDividendDocs,
    calcDividendPolicy,
    calcShareholderReturn,
    calcTreasuryStockStatus,
)
from dartlab.analysis.financial._capitalAllocationReinvest import (
    calcCapitalAllocationFlags,
    calcFcfUsage,
    calcReinvestment,
)

__all__ = [
    "_edgarTreasuryStockFallback",
    "calcCapitalAllocationFlags",
    "calcDividendDocs",
    "calcDividendPolicy",
    "calcFcfUsage",
    "calcReinvestment",
    "calcShareholderReturn",
    "calcTreasuryStockStatus",
]

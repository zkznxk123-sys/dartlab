"""재무 횡단 스캔 — 비율 7 축 (성장·수익·효율·품질·유동성·현금흐름·밸류에이션).

라우터의 `_SCAN_GROUPS["financial"]` 그룹 멤버를 SSOT 폴더로 묶는다.
호출 진입점은 `dartlab.scan("financial", "...")` 또는 각 서브모듈 직접.
"""

from __future__ import annotations

from dartlab.scan.financial.cashflow import scanCashflow
from dartlab.scan.financial.efficiency import scanEfficiency
from dartlab.scan.financial.growth import _computeGrowth, scanGrowth
from dartlab.scan.financial.liquidity import scanLiquidity
from dartlab.scan.financial.profitability import _computeProfitability, scanProfitability
from dartlab.scan.financial.quality import scanQuality
from dartlab.scan.financial.valuation import fetchValuationRaw, scanValuation

__all__ = [
    "scanCashflow",
    "scanEfficiency",
    "scanGrowth",
    "scanLiquidity",
    "scanProfitability",
    "scanQuality",
    "scanValuation",
    "fetchValuationRaw",
    "_computeGrowth",
    "_computeProfitability",
]

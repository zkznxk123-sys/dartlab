"""Act 3 selector: 현금흐름 + 이익품질."""
from __future__ import annotations
from typing import Any
from dartlab.ai.context.bundle import ContextPart, PartPriority
from dartlab.ai.context.selectors._calc_base import _buildParts


def selectAct3(company: Any, basePeriod: str | None = None) -> list[ContextPart]:
    if company is None:
        return []
    try:
        from dartlab.analysis.financial.cashflow import calcCashFlowOverview, calcCashQuality
        from dartlab.analysis.financial.earningsQuality import calcAccrualAnalysis
    except ImportError:
        return []
    return _buildParts(company, [
        ("act3.cashflow", "현금흐름 개요", calcCashFlowOverview, PartPriority.HIGH),
        ("act3.quality", "현금 품질", calcCashQuality, PartPriority.HIGH),
        ("act3.accrual", "발생액 분석", calcAccrualAnalysis, PartPriority.MEDIUM),
    ], basePeriod)

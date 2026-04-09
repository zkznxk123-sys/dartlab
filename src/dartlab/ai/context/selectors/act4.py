"""Act 4 selector: 안정성 (자금조달 + 레버리지 + 부실판별)."""
from __future__ import annotations
from typing import Any
from dartlab.ai.context.bundle import ContextPart, PartPriority
from dartlab.ai.context.selectors._calc_base import _buildParts


def selectAct4(company: Any, basePeriod: str | None = None) -> list[ContextPart]:
    if company is None:
        return []
    try:
        from dartlab.analysis.financial.capital import calcFundingSources
        from dartlab.analysis.financial.stability import calcDistressScore, calcLeverageTrend
    except ImportError:
        return []
    return _buildParts(company, [
        ("act4.funding", "자금 원천", calcFundingSources, PartPriority.HIGH),
        ("act4.leverage", "레버리지 추이", calcLeverageTrend, PartPriority.HIGH),
        ("act4.distress", "부실 판별", calcDistressScore, PartPriority.MEDIUM),
    ], basePeriod)

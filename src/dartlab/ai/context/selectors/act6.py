"""Act 6 selector: 전망 (가치평가 + 신용)."""
from __future__ import annotations
from typing import Any
from dartlab.ai.context.bundle import ContextPart, PartPriority
from dartlab.ai.context.selectors._calc_base import _buildParts


def selectAct6(company: Any, basePeriod: str | None = None) -> list[ContextPart]:
    if company is None:
        return []
    calcs: list[tuple[str, str, Any, PartPriority]] = []
    try:
        from dartlab.analysis.financial.valuation import calcValuationSynthesis
        calcs.append(("act6.valuation", "가치평가 종합", calcValuationSynthesis, PartPriority.HIGH))
    except ImportError:
        pass
    try:
        from dartlab.credit.calcs import calcCreditScore
        calcs.append(("act6.credit", "신용등급", calcCreditScore, PartPriority.MEDIUM))
    except ImportError:
        pass
    if not calcs:
        return []
    return _buildParts(company, calcs, basePeriod)

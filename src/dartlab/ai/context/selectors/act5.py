"""Act 5 selector: 자본배분 (자산구조 + ROIC + 배당)."""

from __future__ import annotations

from typing import Any

from dartlab.ai.context.bundle import ContextPart, PartPriority
from dartlab.ai.context.selectors._calc_base import _buildParts


def selectAct5(company: Any, basePeriod: str | None = None) -> list[ContextPart]:
    if company is None:
        return []
    try:
        from dartlab.analysis.financial.asset import calcAssetStructure
        from dartlab.analysis.financial.capitalAllocation import calcDividendPolicy
        from dartlab.analysis.financial.investmentAnalysis import calcRoicTimeline
    except ImportError:
        return []
    return _buildParts(
        company,
        [
            ("act5.asset", "자산 구조", calcAssetStructure, PartPriority.HIGH),
            ("act5.roic", "ROIC 추이", calcRoicTimeline, PartPriority.HIGH),
            ("act5.dividend", "배당 정책", calcDividendPolicy, PartPriority.MEDIUM),
        ],
        basePeriod,
    )

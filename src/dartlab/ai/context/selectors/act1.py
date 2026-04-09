"""Act 1 selector: 사업이해 (수익구조 + 성장성)."""

from __future__ import annotations
from typing import Any
from dartlab.ai.context.bundle import ContextPart, PartPriority
from dartlab.ai.context.selectors._calc_base import _buildParts


def selectAct1(company: Any, basePeriod: str | None = None) -> list[ContextPart]:
    if company is None:
        return []
    try:
        from dartlab.analysis.financial.revenue import (
            calcConcentration,
            calcRevenueGrowth,
            calcSegmentComposition,
        )
    except ImportError:
        return []
    return _buildParts(
        company,
        [
            ("act1.segments", "매출 구성", calcSegmentComposition, PartPriority.HIGH),
            ("act1.growth", "매출 성장", calcRevenueGrowth, PartPriority.HIGH),
            ("act1.concentration", "매출 집중도", calcConcentration, PartPriority.MEDIUM),
        ],
        basePeriod,
    )

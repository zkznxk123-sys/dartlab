"""Act 2 selector: 수익성 (마진 + 수익률 + DuPont)."""
from __future__ import annotations
from typing import Any
from dartlab.ai.context.bundle import ContextPart, PartPriority
from dartlab.ai.context.selectors._calc_base import _buildParts


def selectAct2(company: Any, basePeriod: str | None = None) -> list[ContextPart]:
    if company is None:
        return []
    try:
        from dartlab.analysis.financial.profitability import (
            calcDupont,
            calcMarginTrend,
            calcReturnTrend,
        )
    except ImportError:
        return []
    return _buildParts(company, [
        ("act2.margin", "마진 추이", calcMarginTrend, PartPriority.HIGH),
        ("act2.return", "수익률 추이", calcReturnTrend, PartPriority.HIGH),
        ("act2.dupont", "DuPont 분해", calcDupont, PartPriority.MEDIUM),
    ], basePeriod)

"""이익의 질 분석 — facade. 본체는 `_earningsQualityCalcs` / `_earningsQualityCompany`.

이익이 현금으로 뒷받침되는지, 일회성인지, 조작 가능성이 있는지를 시계열로 추적한다.
"""

from __future__ import annotations

from dartlab.analysis.financial._earningsQualityCalcs import (
    _beneishInterpretation,
    _calcEarningsQualityFlagsBase,
    calcBeneishMScore,
    calcSloanAccruals,
    detectAuditFlags,
)
from dartlab.analysis.financial._earningsQualityCompany import (
    calcAccrualAnalysis,
    calcEarningsPersistence,
    calcEarningsQualityFlags,
)

# 분리된 깊이 분석 (BC re-export)
from dartlab.analysis.financial._earningsQualityDeep import (  # noqa: E402, F401
    calcBeneishTimeline,
    calcDilutionTrend,
    calcNonOperatingBreakdown,
    calcQualityAnomalies,
    calcRichardsonAccrual,
)

__all__ = [
    "_beneishInterpretation",
    "_calcEarningsQualityFlagsBase",
    "calcAccrualAnalysis",
    "calcBeneishMScore",
    "calcBeneishTimeline",
    "calcDilutionTrend",
    "calcEarningsPersistence",
    "calcEarningsQualityFlags",
    "calcNonOperatingBreakdown",
    "calcQualityAnomalies",
    "calcRichardsonAccrual",
    "calcSloanAccruals",
    "detectAuditFlags",
]

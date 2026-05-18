"""earningsQuality.py 깊이 분석 — facade. 본체는 `_earningsQualityDeepProxies` /
`_earningsQualityDeepBeneish` / `_earningsQualityDeepAccrual` / `_earningsQualityDeepDilution`.

calcBeneishTimeline + calcRichardsonAccrual + calcNonOperatingBreakdown +
calcDilutionTrend + calcQualityAnomalies + 8 lazy proxies.
"""

from __future__ import annotations

from dartlab.analysis.financial._earningsQualityDeepAccrual import (
    calcNonOperatingBreakdown,
    calcRichardsonAccrual,
)
from dartlab.analysis.financial._earningsQualityDeepBeneish import calcBeneishTimeline
from dartlab.analysis.financial._earningsQualityDeepDilution import (
    calcDilutionTrend,
    calcQualityAnomalies,
)
from dartlab.analysis.financial._earningsQualityDeepProxies import (
    _beneishInterpretation,
    _calcEarningsQualityFlagsBase,
    calcAccrualAnalysis,
    calcBeneishMScore,
    calcEarningsPersistence,
    calcEarningsQualityFlags,
    calcSloanAccruals,
    detectAuditFlags,
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

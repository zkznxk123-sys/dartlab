"""1-1 수익 구조 분석 — facade. 본체는 `_revenueSelect` / `_revenueSegment` / `_revenueGrowth` / `_revenueQuality`.

블록 조립은 story/sections/revenue.py가 한다.
여기는 company.select() → 계산 → dict/숫자 반환.

데이터 접근: select() 단일 경로.
- 부문별 매출: select("productService") → 항목×기간 수평화 DF
- 지역/제품별: select("salesOrder") → 항목×기간 수평화 DF
- 재무제표: select("IS", [...]) → 숫자 DF
"""

from __future__ import annotations

from dartlab.analysis.financial._revenueGrowth import (
    calcConcentration,
    calcFlags,
    calcGrowthContribution,
    calcRevenueGrowth,
)
from dartlab.analysis.financial._revenueQuality import calcRevenueQuality
from dartlab.analysis.financial._revenueSegment import (
    calcBreakdown,
    calcCompanyProfile,
    calcSegmentComposition,
    calcSegmentTrend,
)
from dartlab.analysis.financial._revenueSelect import (
    _MAX_SEGMENTS,
    _MAX_YEARS,
    _SKIP_KEYWORDS,
    _getRatios,
    _selectDocsOpIncome,
    _selectDocsRevenue,
    _selectDocsSalesOrder,
)

__all__ = [
    "_MAX_SEGMENTS",
    "_MAX_YEARS",
    "_SKIP_KEYWORDS",
    "_getRatios",
    "_selectDocsOpIncome",
    "_selectDocsRevenue",
    "_selectDocsSalesOrder",
    "calcBreakdown",
    "calcCompanyProfile",
    "calcConcentration",
    "calcFlags",
    "calcGrowthContribution",
    "calcRevenueGrowth",
    "calcRevenueQuality",
    "calcSegmentComposition",
    "calcSegmentTrend",
]

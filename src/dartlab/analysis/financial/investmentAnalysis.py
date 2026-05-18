"""투자 분석 — facade. 본체는 `_investmentAnalysisRoic` / `_investmentAnalysisEva`.

select()로 IS/BS/CF 원본 계정을 가져와서
투자가 실제로 가치를 만드는지를 금액과 함께 시계열로 추적한다.
"""

from __future__ import annotations

from dartlab.analysis.financial._investmentAnalysisEva import (
    calcEvaTimeline,
    calcInvestmentFlags,
    calcInvestmentInOther,
)
from dartlab.analysis.financial._investmentAnalysisRoic import (
    _estimateWacc,
    _yoy,
    calcInvestmentIntensity,
    calcRoicTimeline,
)

__all__ = [
    "_estimateWacc",
    "_yoy",
    "calcEvaTimeline",
    "calcInvestmentFlags",
    "calcInvestmentInOther",
    "calcInvestmentIntensity",
    "calcRoicTimeline",
]

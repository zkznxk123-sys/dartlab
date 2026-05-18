"""1-2 자금 구조 분석 — facade. 본체는 `_capitalStructure` / `_capitalLiquidity`.

블록 조립은 story/builders.py가 한다.
여기는 company.select() → 계산 → dict/숫자 반환.
"""

from __future__ import annotations

from dartlab.analysis.financial._capitalLiquidity import (
    _calcFinDebtPct,
    _calcRetainedPct,
    calcLiquidity,
)
from dartlab.analysis.financial._capitalStructure import (
    _MAX_QUARTERS,
    _MAX_YEARS,
    _buildCapitalTable,
    _buildDebtTable,
    _calcImpliedBorrowingRate,
    _calcNetDebtEbitda,
    _fmtAmt,
    _getRatios,
    _latestAnnualVal,
    _quarterlyCols,
    calcCapitalOverview,
    calcCapitalTimeline,
    calcDebtTimeline,
    calcInterestBurden,
)

__all__ = [
    "_MAX_QUARTERS",
    "_MAX_YEARS",
    "_buildCapitalTable",
    "_buildDebtTable",
    "_calcFinDebtPct",
    "_calcImpliedBorrowingRate",
    "_calcNetDebtEbitda",
    "_calcRetainedPct",
    "_fmtAmt",
    "_getRatios",
    "_latestAnnualVal",
    "_quarterlyCols",
    "calcCapitalOverview",
    "calcCapitalTimeline",
    "calcDebtTimeline",
    "calcInterestBurden",
    "calcLiquidity",
]

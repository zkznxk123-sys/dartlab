"""데이터 표시 — 카테고리 데이터 (finance/...) + 매체 렌더러 (rich/HTML).

- finance/ — 재무 데이터 → 표준 JSON View 14 종 (frontend 진입점, VIEWS)
- rich/HTML — Company/Result __repr__ 매체 (구 richCompany/richFrame/richInsight 등)
"""

from __future__ import annotations

# 카테고리 데이터
from dartlab.viz.display.finance import VIEWS as FINANCE_VIEWS

# 매체 렌더러 (REPL/Jupyter)
from dartlab.viz.display.notebook import htmlDistress, htmlFinance, htmlInsight, interactiveTable
from dartlab.viz.display.richCompany import renderCompany
from dartlab.viz.display.richFrame import renderFinance, show
from dartlab.viz.display.richIndex import renderIndex, showIndex
from dartlab.viz.display.richInsight import renderInsight
from dartlab.viz.display.richRatio import renderRatio, showRatio

__all__ = [
    "FINANCE_VIEWS",
    "htmlDistress",
    "htmlFinance",
    "htmlInsight",
    "interactiveTable",
    "renderCompany",
    "renderFinance",
    "renderIndex",
    "renderInsight",
    "renderRatio",
    "show",
    "showIndex",
    "showRatio",
]

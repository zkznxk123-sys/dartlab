"""Rich + HTML 데이터 표시 도구."""

from __future__ import annotations

from dartlab.viz.display.notebook import htmlDistress, htmlFinance, htmlInsight, interactiveTable
from dartlab.viz.display.richCompany import renderCompany
from dartlab.viz.display.richFrame import renderFinance, show
from dartlab.viz.display.richIndex import renderIndex, showIndex
from dartlab.viz.display.richInsight import renderInsight
from dartlab.viz.display.richRatio import renderRatio, showRatio

__all__ = [
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

"""차트 렌더러 Protocol — viz 가 구현해 core 가 lookup."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ChartHtmlRenderer(Protocol):
    """ChartSpec dict → HTML 문자열 변환기.

    viz/plotly 가 PlotlyChartRenderer 로 구현. matplotlib/altair 등 다른
    백엔드도 같은 Protocol 따르면 등록 가능.
    """

    def htmlFromSpec(self, spec: dict) -> str:
        """ChartSpec → HTML 문자열 (Plotly to_html 등)."""
        ...

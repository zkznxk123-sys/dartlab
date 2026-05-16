"""viz/display 의 HtmlRenderer Protocol 구현 — core/htmlRenderer 등록.

analysis/financial 의 RatioResult/InsightResult/DistressResult/AnalysisResult 의
__repr__/_repr_html_ 가 호출. import 시점 자동 register — analysis 는 core 만 import 하고
viz 직접 의존 안 함.
"""

from __future__ import annotations

from typing import Any

from dartlab.core.htmlRenderer import registerHtmlRenderer


class VizHtmlRenderer:
    """viz/display 의 4 함수 (renderRatio · renderInsight · htmlDistress · htmlInsight)
    위임체 — HtmlRenderer Protocol 구현."""

    def renderRatio(self, result: Any) -> str | None:
        """RatioResult → rich 콘솔 텍스트. rich 미설치 시 None."""
        try:
            from rich.console import Console

            from dartlab.viz.display.richRatio import renderRatio

            console = Console(record=True, width=70)
            console.print(renderRatio(result))
            return console.export_text()
        except ImportError:
            return None

    def renderInsight(self, result: Any) -> str | None:
        """AnalysisResult → rich 텍스트. rich 미설치 시 None."""
        try:
            from dartlab.viz.display.richInsight import renderInsight

            return renderInsight(result)
        except ImportError:
            return None

    def htmlDistress(self, result: Any) -> str | None:
        """DistressResult → HTML. viz/display 미설치 시 None."""
        try:
            from dartlab.viz.display.notebook import htmlDistress

            return htmlDistress(result)
        except ImportError:
            return None

    def htmlInsight(self, result: Any) -> str | None:
        """AnalysisResult → HTML. viz/display 미설치 시 None."""
        try:
            from dartlab.viz.display.notebook import htmlInsight

            return htmlInsight(result)
        except ImportError:
            return None

    def renderCompany(self, company: Any) -> str | None:
        """Company facade → rich 텍스트. 실패 시 None."""
        try:
            from dartlab.viz.display.richCompany import renderCompany

            return renderCompany(company)
        except ImportError:
            return None

    def renderNetwork(self, *args: Any, **kwargs: Any) -> Any | None:
        """네트워크 그래프 → 렌더 — viz.network.renderNetwork 위임. 실패 시 None."""
        try:
            from dartlab.viz.renderers.network import renderNetwork

            return renderNetwork(*args, **kwargs)
        except ImportError:
            return None


registerHtmlRenderer(VizHtmlRenderer())

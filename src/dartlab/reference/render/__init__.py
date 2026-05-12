"""차트 렌더링 protocol + registry — viz 의 plotly/matplotlib 의존 역전.

core 는 ChartSpec dict 만 만들고, 실제 HTML/PNG 렌더는 viz 가 등록한
ChartHtmlRenderer 구현이 담당. core → viz 의존을 끊는 패턴.

사용 흐름:
    1. dartlab import 시점에 viz/__init__.py 가 register(PlotlyChartRenderer()) 호출
    2. core/select.py 의 _renderHtml 이 getRenderer().htmlFromSpec(spec) 호출
    3. plotly 미설치 환경 (pyodide 등) 은 register 자체가 안 되어 None → markdown fallback
"""

from dartlab.reference.render.protocols import ChartHtmlRenderer
from dartlab.reference.render.registry import getRenderer, register

__all__ = ["ChartHtmlRenderer", "getRenderer", "register"]

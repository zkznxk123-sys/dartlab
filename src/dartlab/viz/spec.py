"""VizSpec — 통합 시각화 스펙 프로토콜.

기존 ChartSpec JSON과 100% 하위호환.
``vizType`` 필드로 chart / diagram 분기.

ChartSpec JSON 프로토콜::

    {
        "chartType": "combo" | "bar" | "line" | "radar" | "waterfall"
                     | "heatmap" | "sparkline" | "pie"
                     | "income-trend-matrix" | "cashflow-signed-matrix"
                     | "balance-structure-trend" | "kpi-ribbon"
                     | "peer-matrix" | "six-act-radar" | "hover-spark"
                     | "evidence-coverage",
        "title": str,
        "series": [
            {
                "name": str,
                "data": [number],
                "color": str,
                "type": "bar"|"line",
                # datapoint 단위 evidence — series.data[i] 와 1:1 대응
                "pointRefs": [{"period": str, "valueRef": str, "rcept_no": str?}],
            }
        ],
        "categories": [str],
        "options": {"unit": str, "stacked": bool, "maxValue": number, ...},
        "meta": {"source": str, "stockCode": str, "corpName": str},
        # 차트 단위 evidence — drill-back 회로의 진입점
        "evidenceBinding": {
            "tableRef": str,        # e.g. "finance:IS:annual"
            "source": str,          # finance / report / docs / scan / industry
            "stockCode": str,
            "topic": str,           # IS / BS / CF / RATIO / PEER / RADAR ...
            "periodKind": str,      # "Y" / "Q" / "MIXED"
            "periods": [str],       # 차트에 포함된 모든 period
        }
    }
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VizSpec:
    """통합 시각화 스펙.

    vizType:
        - ``"chart"``: 데이터 차트 (combo/bar/line/radar/waterfall/heatmap/sparkline/pie)
        - ``"diagram"``: 다이어그램 (mermaid 등)

    chart 모드일 때 ``toDict()`` 출력은 기존 ChartSpec JSON과 동일
    → Svelte ``ChartRenderer`` 변경 0줄.
    """

    vizType: str = "chart"

    # ── chart ──
    chartType: str = ""
    title: str = ""
    series: list[dict[str, Any]] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    options: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)
    purpose: str = ""
    evidenceIds: list[str] = field(default_factory=list)
    # 차트 단위 evidence binding — drill-back 회로의 진입점.
    # generator 가 채우면 emit_chart 가드를 통과한다. 비어 있으면 거부.
    evidenceBinding: dict[str, Any] = field(default_factory=dict)

    # ── diagram ──
    diagramType: str = ""
    source: str = ""

    # ── 변환 ──

    def toDict(self) -> dict[str, Any]:
        """ChartSpec 호환 JSON dict.

        vizType=chart → 기존 ChartSpec 필드만 포함 (하위호환).
        vizType=diagram → vizType, diagramType, source, title, meta.
        """
        if self.vizType == "diagram":
            out = {
                "vizType": "diagram",
                "diagramType": self.diagramType,
                "source": self.source,
                "title": self.title,
                "meta": self.meta,
            }
            if self.purpose:
                out["purpose"] = self.purpose
            if self.evidenceIds:
                out["evidenceIds"] = self.evidenceIds
            if self.evidenceBinding:
                out["evidenceBinding"] = self.evidenceBinding
            return out
        out = {
            "chartType": self.chartType,
            "title": self.title,
            "series": self.series,
            "categories": self.categories,
            "options": self.options,
            "meta": self.meta,
        }
        if self.purpose:
            out["purpose"] = self.purpose
        if self.evidenceIds:
            out["evidenceIds"] = self.evidenceIds
        if self.evidenceBinding:
            out["evidenceBinding"] = self.evidenceBinding
        return out

    def toJson(self) -> str:
        """JSON 문자열."""
        return json.dumps(self.toDict(), ensure_ascii=False, default=str)

    def toPlotly(self) -> Any:
        """Plotly Figure (lazy import).

        Raises:
            ImportError: plotly 미설치 시.
        """
        from dartlab.viz.plotly import fromSpec

        return fromSpec(self.toDict())

    def toHtml(self) -> str:
        """Plotly HTML (CDN, fragment)."""
        fig = self.toPlotly()
        return fig.to_html(include_plotlyjs="cdn", full_html=False)

    def toImage(self, path: str, fmt: str = "svg") -> bool:
        """Plotly → 정적 이미지 저장. kaleido 필요.

        Returns True on success, False on failure (kaleido 미설치 등).
        """
        try:
            fig = self.toPlotly()
            fig.write_image(path, format=fmt, width=800, height=400)
            return True
        except (ImportError, ValueError, OSError):
            return False

    def toSvgRaw(self, width: int = 800, height: int = 400) -> str:
        """경량 SVG 문자열 (kaleido 불필요).

        landing 컴포넌트와 유사한 간결한 SVG. bar/line/sparkline/pie/combo 지원.
        """
        from dartlab.viz.svg import renderSvg

        return renderSvg(self.toDict(), width=width, height=height)

    def toAscii(self, width: int = 80, height: int = 20) -> str:
        """터미널용 ASCII/ANSI 차트.

        bar/line/sparkline 지원. plotext 우선, 없으면 fallback.
        """
        from dartlab.viz.ascii import renderAscii

        return renderAscii(self.toDict(), width=width, height=height)

    def _repr_html_(self) -> str:
        """Jupyter/IPython 자동 렌더 훅."""
        try:
            return self.toHtml()
        except Exception:
            return f"<pre>{self.toJson()}</pre>"

    def _repr_mimebundle_(self, include=None, exclude=None) -> dict[str, Any]:
        """Marimo/IPython MIME bundle 렌더.

        text/html (Plotly 기본) + application/vnd.plotly.v1+json (Marimo 선호).
        """
        try:
            return {
                "text/html": self.toHtml(),
                "application/vnd.plotly.v1+json": self.toDict(),
            }
        except Exception:
            return {"text/plain": self.toJson()}

    @staticmethod
    def fromDict(d: dict[str, Any]) -> "VizSpec":
        """dict → VizSpec 변환."""
        viz_type = d.get("vizType", "chart")
        if viz_type == "diagram":
            return VizSpec(
                vizType="diagram",
                diagramType=d.get("diagramType", ""),
                source=d.get("source", ""),
                title=d.get("title", ""),
                meta=d.get("meta", {}),
                purpose=d.get("purpose", ""),
                evidenceIds=d.get("evidenceIds", []),
                evidenceBinding=d.get("evidenceBinding", {}),
            )
        return VizSpec(
            vizType="chart",
            chartType=d.get("chartType", ""),
            title=d.get("title", ""),
            series=d.get("series", []),
            categories=d.get("categories", []),
            options=d.get("options", {}),
            meta=d.get("meta", {}),
            purpose=d.get("purpose", ""),
            evidenceIds=d.get("evidenceIds", []),
            evidenceBinding=d.get("evidenceBinding", {}),
        )

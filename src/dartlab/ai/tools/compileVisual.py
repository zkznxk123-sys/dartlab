"""compile_visual tool — LLM 자율 시각화 spec 발급.

LLM 이 분석 결과를 차트·표로 표현하고 싶을 때 호출. data + chartType 입력 →
viewSpec.normalizeViewSpec 가 받는 spec 반환 (visualRef).

agent.py 가 tool 결과의 visualRef 감지 시 VIEW_SPEC event 발행 → ChartRenderer 인라인.

휴리스틱 chartType (LLM 이 결정 — 이 도구는 단순 spec 변환):
- "line"      : 시계열 (x=date, y=numeric)
- "bar"       : 비교 (x=category, y=numeric)
- "table"     : 표 (data 그대로)
- "radar"     : 다축 비교
- "waterfall" : 증감 누적
- "heatmap"   : 매트릭스
- "histogram" : 분포
"""

from __future__ import annotations

import uuid
from typing import Any

from dartlab.ai.contracts import Ref

from .types import ToolResult

_VALID_CHART_TYPES = {"line", "bar", "table", "radar", "waterfall", "heatmap", "histogram"}


def compileVisual(
    chartType: str = "line",
    data: list[dict[str, Any]] | None = None,
    title: str | None = None,
    xAxis: str | None = None,
    yAxis: str | None = None,
    subtitle: str | None = None,
    source: str | None = None,
    **_extra: Any,
) -> ToolResult:
    """data + chartType → visualRef. ChartRenderer 가 인라인 렌더."""
    if not data or not isinstance(data, list):
        return ToolResult(False, "data 가 비어 있거나 list 가 아닙니다", error="invalid_data")
    chart = (chartType or "line").lower()
    if chart not in _VALID_CHART_TYPES:
        return ToolResult(
            False,
            f"지원하지 않는 chartType: {chart}. 허용: {', '.join(sorted(_VALID_CHART_TYPES))}",
            error="invalid_chart_type",
        )

    spec: dict[str, Any] = {
        "type": chart,
        "data": data,
    }
    if xAxis or yAxis:
        spec["axis"] = {"x": xAxis, "y": yAxis}
    if title:
        spec["title"] = title
    if subtitle:
        spec["subtitle"] = subtitle
    if source:
        spec["source"] = source

    refId = f"visual:{chart}:{uuid.uuid4().hex[:8]}"
    ref = Ref(
        id=refId,
        kind="visualRef",
        title=title or f"{chart} chart",
        source=source or "",
        payload={"spec": spec, "chartType": chart, "rowCount": len(data)},
    )
    summary = f"{chart} chart spec ({len(data)} rows)"
    if title:
        summary = f"{title} — {summary}"
    return ToolResult(True, summary, refs=[ref], data={"spec": spec})

"""View → recharts 호환 JSON spec.

web 의 `<VizChart spec={...}/>` 디스패처가 받아 recharts 컴포넌트로 분기.
출력은 *JSON 직렬화 가능*한 dict — `/api/viz/dashboard/{code}` 응답 페이로드.

매핑:
- kind="trend" + series.type 다양 → recharts `ComposedChart` (bar + line + area 혼합)
- kind="trend" + series.type 단일 "line" → `LineChart`
- kind="trend" + series.type 단일 "bar" → `BarChart`
- kind="breakdown" → `PieChart`
- kind="radar" → `RadarChart`
- kind="waterfall" → ComposedChart with stacked bars (recharts 네이티브 미지원, web 측 어댑터가 처리)
- kind="table" → 그대로 dict 반환 (web 측이 HTML table 그림)

paletteOverride 는 series.key 또는 series.intent 키로 hex 매핑.
"""

from __future__ import annotations

from typing import Any

from dartlab.viz.palette import resolveColor
from dartlab.viz.schema import View


def _rechartsType(kind: str, seriesTypes: set[str]) -> str:
    """recharts 컴포넌트 이름 결정."""
    if kind == "breakdown":
        return "PieChart"
    if kind == "radar":
        return "RadarChart"
    if kind == "table":
        return "Table"
    if kind == "waterfall":
        return "Waterfall"
    if kind == "trend":
        if seriesTypes <= {"line"}:
            return "LineChart"
        if seriesTypes <= {"bar"}:
            return "BarChart"
        return "ComposedChart"
    return "ComposedChart"


def toRechartsSpec(
    view: View,
    paletteOverride: dict[str, str] | None = None,
) -> dict[str, Any]:
    """View → recharts JSON spec.

    Args:
        view: builder.buildView 결과.
        paletteOverride: 시리즈 key 또는 intent → hex 매핑.
            web 측에서 `{primary: 'var(--chart-1)', ...}` 로 토큰 매핑 가능.

    Returns:
        recharts JSON spec dict. JSON 직렬화 가능.
    """
    series = view.get("series") or []
    seriesTypes: set[str] = {s.get("type", "bar") for s in series if isinstance(s, dict)}
    componentType = _rechartsType(view.get("kind", "trend"), seriesTypes)

    resolvedSeries: list[dict[str, Any]] = []
    for s in series:
        color = resolveColor(
            color=s.get("color"),
            intent=s.get("intent"),
            key=s.get("key"),
            override=paletteOverride,
        )
        entry: dict[str, Any] = {
            "key": s.get("key"),
            "label": s.get("label", ""),
            "color": color,
            "type": s.get("type", "bar"),
            "data": s.get("data") or [],
        }
        if "unit" in s:
            entry["unit"] = s["unit"]
        if "axis" in s:
            entry["axis"] = s["axis"]
        if "stack" in s:
            entry["stack"] = s["stack"]
        if "intent" in s:
            entry["intent"] = s["intent"]
        resolvedSeries.append(entry)

    out: dict[str, Any] = {
        "componentType": componentType,
        "kind": view.get("kind", "trend"),
        "title": view.get("title", ""),
        "categories": view.get("categories") or [],
        "series": resolvedSeries,
        "options": view.get("options") or {},
        "evidenceBinding": view.get("evidenceBinding") or {},
        "meta": view.get("meta") or {},
    }

    # kind 별 추가 필드 — kpiTile/diffView/topList/comparisonTable/gauge/phaseIndicator/sankey/scatter/matrix.
    # 한 view 가 자기 kind 에 해당하는 필드만 갖고 있음 — 있으면 그대로 전달.
    for extra in (
        "tiles",
        "periodLabel",  # kpiTile/diffView
        "items",
        "direction",  # topList
        "rows",
        "peerCount",  # comparisonTable
        "value",
        "minValue",
        "maxValue",
        "bands",
        "subtitle",  # gauge
        "phases",
        "current",
        "confidence",
        "phaseHistory",  # phaseIndicator
        "nodes",
        "links",  # sankey
        "points",
        "xLabel",
        "yLabel",
        "xUnit",
        "yUnit",
        "xRef",
        "yRef",  # scatter
        "cells",
        "rowOrder",
        "colOrder",
        "tone",  # heatmap (matrix)
        "layout",  # bento packing (colSpan, rowSpan)
    ):
        if extra in view:
            out[extra] = view[extra]
    return out


__all__ = ["toRechartsSpec"]

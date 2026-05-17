"""View → 경량 SVG (kaleido 미설치 환경 + blog/sns).

renderers/svg.py 의 기존 renderSvg 가 옛 ChartSpec 포맷 입력 — 그쪽에 위임할
어댑터를 거쳐 호출한다.
"""

from __future__ import annotations

from dartlab.viz.palette import resolveColor
from dartlab.viz.schema import View


def _viewToLegacySpec(view: View, paletteOverride: dict[str, str] | None) -> dict:
    """View → 옛 ChartSpec 포맷 (renderers/svg.renderSvg 호환).

    chartType 매핑:
    - trend (bar 만, stacked) → "bar"
    - trend (line 만) → "line"
    - trend (혼합) → "combo"
    - breakdown → "pie"
    - waterfall → "waterfall"
    - radar → "radar"
    - 기타 → "bar"
    """
    series = view.get("series") or []
    types = {s.get("type", "bar") for s in series if isinstance(s, dict)}
    kind = view.get("kind", "trend")

    if kind == "trend":
        if types <= {"line"}:
            chartType = "line"
        elif types <= {"bar"}:
            chartType = "bar"
        else:
            chartType = "combo"
    elif kind == "breakdown":
        chartType = "pie"
    else:
        chartType = kind

    legacySeries = []
    for s in series:
        legacySeries.append(
            {
                "name": s.get("label", ""),
                "data": s.get("data") or [],
                "color": resolveColor(
                    color=s.get("color"),
                    intent=s.get("intent"),
                    key=s.get("key"),
                    override=paletteOverride,
                ),
                "type": s.get("type", "bar"),
            }
        )

    return {
        "chartType": chartType,
        "title": view.get("title", ""),
        "series": legacySeries,
        "categories": view.get("categories") or [],
        "options": view.get("options") or {},
        "meta": view.get("meta") or {},
    }


def toSvg(
    view: View,
    paletteOverride: dict[str, str] | None = None,
    *,
    width: int = 800,
    height: int = 400,
) -> str:
    """View → SVG 문자열. blog/sns 자산 export.

    Args:
        view: builder.buildView 결과.
        paletteOverride: series.key 또는 intent → hex.
        width: SVG 가로 (px).
        height: SVG 세로 (px).

    Returns:
        SVG 문자열. `<svg>` 루트.
    """
    from dartlab.viz.renderers.svg import renderSvg

    legacy = _viewToLegacySpec(view, paletteOverride)
    return renderSvg(legacy, width=width, height=height)


__all__ = ["toSvg"]

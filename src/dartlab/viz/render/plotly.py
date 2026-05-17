"""View → Plotly Figure.

jupyter/marimo `.show()` + blog/sns PNG export + `_repr_html_` 진입점.

kind 별 분기:
- trend (bar 만) → go.Figure(go.Bar ...)
- trend (line 만) → go.Figure(go.Scatter mode=lines+markers)
- trend (혼합) → make_subplots(secondary_y=True) — bar 는 left, line + axis=right 는 right
- breakdown → go.Pie
- radar → go.Scatterpolar
- waterfall → go.Waterfall (points/measure 가 있을 때만)
- table → go.Table
"""

from __future__ import annotations

from typing import Any

from dartlab.viz.palette import TONE_MAP, resolveColor
from dartlab.viz.schema import View


def _ensurePlotly() -> Any:
    """plotly lazy import."""
    try:
        import plotly.graph_objects as go

        return go
    except ImportError as exc:
        raise ImportError("plotly 패키지가 필요합니다. pip install plotly") from exc


def _resolved(series: list[dict], override: dict[str, str] | None) -> list[dict]:
    """series 의 color 를 resolveColor 로 일괄 치환."""
    out: list[dict] = []
    for s in series:
        out.append(
            {
                **s,
                "color": resolveColor(
                    color=s.get("color"),
                    intent=s.get("intent"),
                    key=s.get("key"),
                    override=override,
                ),
            }
        )
    return out


def _applyTheme(fig: Any, tone: str) -> None:
    """tone (light/dark) 적용."""
    palette = TONE_MAP.get(tone, TONE_MAP["light"])
    fig.update_layout(
        font_family="Pretendard, -apple-system, sans-serif",
        plot_bgcolor=palette["background"],
        paper_bgcolor=palette["background"],
        font=dict(color=palette["foreground"]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=60, r=20, t=60, b=40),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor=palette["grid"], gridwidth=1)
    fig.update_yaxes(showgrid=True, gridcolor=palette["grid"], gridwidth=1)


def _trendFigure(go: Any, view: View, series: list[dict]) -> Any:
    """trend kind 의 figure."""
    types = {s.get("type", "bar") for s in series}
    hasRight = any(s.get("axis") == "right" for s in series)
    categories = view.get("categories") or []

    if hasRight:
        from plotly.subplots import make_subplots

        fig = make_subplots(specs=[[{"secondary_y": True}]])
    else:
        fig = go.Figure()

    options = view.get("options") or {}
    barmode = "stack" if options.get("stacked") else "group"

    for s in series:
        stype = s.get("type", "bar")
        right = s.get("axis") == "right"
        kwargs = {"name": s.get("label", ""), "x": categories, "y": s.get("data") or []}
        if stype == "bar":
            trace = go.Bar(**kwargs, marker_color=s["color"])
        else:
            trace = go.Scatter(
                **kwargs,
                mode="lines+markers",
                line=dict(color=s["color"], width=2),
                marker=dict(size=6),
            )
        if hasRight:
            fig.add_trace(trace, secondary_y=right)
        else:
            fig.add_trace(trace)

    fig.update_layout(title=view.get("title", ""), barmode=barmode)
    if "bar" in types and len(types) > 1:
        # combo: bar 는 y, line 은 secondary y
        pass
    return fig


def _breakdownFigure(go: Any, view: View, series: list[dict]) -> Any:
    """breakdown — pie."""
    categories = view.get("categories") or []
    first = series[0] if series else {"data": []}
    return go.Figure(
        go.Pie(
            labels=categories,
            values=first.get("data") or [],
            marker=dict(colors=[s.get("color") for s in series] or None),
            textinfo="label+percent",
        )
    )


def _radarFigure(go: Any, view: View, series: list[dict]) -> Any:
    """radar — Scatterpolar."""
    categories = view.get("categories") or []
    fig = go.Figure()
    for s in series:
        fig.add_trace(
            go.Scatterpolar(
                r=s.get("data") or [],
                theta=categories,
                fill="toself",
                name=s.get("label", ""),
                line=dict(color=s["color"]),
            )
        )
    fig.update_layout(title=view.get("title", ""))
    return fig


def _waterfallFigure(go: Any, view: View, series: list[dict]) -> Any:
    """waterfall — go.Waterfall."""
    categories = view.get("categories") or []
    first = series[0] if series else {"data": []}
    data = first.get("data") or []
    measures = ["relative"] * max(0, len(data) - 1) + (["total"] if data else [])
    return go.Figure(
        go.Waterfall(
            x=categories,
            y=data,
            measure=measures,
            connector=dict(line=dict(color="#888", width=1)),
        )
    )


def toPlotly(
    view: View,
    paletteOverride: dict[str, str] | None = None,
    *,
    tone: str = "light",
) -> Any:
    """View → Plotly Figure.

    Args:
        view: builder.buildView 결과.
        paletteOverride: series.key 또는 intent → hex.
        tone: "light" | "dark" — TONE_MAP 적용.

    Returns:
        plotly.graph_objects.Figure. `.show()` / `.to_html()` / `.write_image()` 가능.
    """
    go = _ensurePlotly()
    series = _resolved(view.get("series") or [], paletteOverride)
    kind = view.get("kind", "trend")

    if kind == "breakdown":
        fig = _breakdownFigure(go, view, series)
    elif kind == "radar":
        fig = _radarFigure(go, view, series)
    elif kind == "waterfall":
        fig = _waterfallFigure(go, view, series)
    else:
        fig = _trendFigure(go, view, series)

    _applyTheme(fig, tone)
    return fig


__all__ = ["toPlotly"]

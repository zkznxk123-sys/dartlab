"""경량 SVG 렌더러 (kaleido 불필요).

VizSpec dict → SVG 문자열. landing 컴포넌트(BarChart.svelte 등)와 유사한 간결한 SVG.
Plotly + kaleido 대안. 정적 export / Markdown 임베드 용도.

지원 chartType: bar, line, sparkline, combo, pie.
radar/waterfall/heatmap → 간이 버전 또는 fallback.
"""

from __future__ import annotations

from html import escape
from typing import Any

_DEFAULT_COLORS = [
    "#ea4647",
    "#fb923c",
    "#3b82f6",
    "#22c55e",
    "#8b5cf6",
    "#06b6d4",
    "#f59e0b",
    "#ec4899",
]
_BG = "#0f1219"
_GRID = "#1e2433"
_TEXT = "#cbd5e1"
_TEXT_DIM = "#64748b"


def _svg_open(width: int, height: int, title: str = "") -> str:
    """SVG 루트 + 배경."""
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" style="font-family:system-ui,sans-serif;">',
        f'<rect width="{width}" height="{height}" fill="{_BG}" rx="6"/>',
    ]
    if title:
        parts.append(f'<text x="14" y="24" fill="{_TEXT}" font-size="13" font-weight="600">{escape(title)}</text>')
    return "\n".join(parts)


def _svg_close() -> str:
    return "</svg>"


def _bar_chart(spec: dict[str, Any], width: int, height: int) -> str:
    series = spec.get("series") or []
    categories = spec.get("categories") or []
    if not series or not categories:
        return _svg_open(width, height, spec.get("title", "")) + _svg_close()

    pad_l, pad_r, pad_t, pad_b = 50, 20, 40, 40
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b

    # 최대값 (모든 시리즈)
    all_vals = [v for s in series for v in (s.get("data") or []) if v is not None]
    max_val = max(all_vals) if all_vals else 1
    max_val = max_val * 1.1

    group_w = plot_w / max(1, len(categories))
    bar_w = group_w / max(1, len(series)) * 0.8

    parts = [_svg_open(width, height, spec.get("title", ""))]

    # y grid 5개
    for i in range(5):
        y = pad_t + plot_h * i / 4
        parts.append(
            f'<line x1="{pad_l}" y1="{y}" x2="{pad_l + plot_w}" y2="{y}" stroke="{_GRID}" stroke-width="0.5"/>'
        )

    # bars
    for si, s in enumerate(series):
        data = s.get("data") or []
        color = s.get("color") or _DEFAULT_COLORS[si % len(_DEFAULT_COLORS)]
        for ci, v in enumerate(data):
            if v is None:
                continue
            h = plot_h * (v / max_val)
            x = pad_l + ci * group_w + si * bar_w + (group_w - bar_w * len(series)) / 2
            y = pad_t + plot_h - h
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="{color}" opacity="0.85"/>'
            )

    # x labels
    for ci, cat in enumerate(categories):
        x = pad_l + ci * group_w + group_w / 2
        y = pad_t + plot_h + 18
        parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" fill="{_TEXT_DIM}" '
            f'font-size="10" text-anchor="middle">{escape(str(cat))}</text>'
        )

    # legend
    for si, s in enumerate(series):
        color = s.get("color") or _DEFAULT_COLORS[si % len(_DEFAULT_COLORS)]
        lx = pad_l + si * 100
        ly = height - 10
        parts.append(
            f'<rect x="{lx}" y="{ly - 8}" width="10" height="10" fill="{color}"/>'
            f'<text x="{lx + 14}" y="{ly}" fill="{_TEXT}" font-size="10">'
            f"{escape(s.get('name', ''))}</text>"
        )

    parts.append(_svg_close())
    return "\n".join(parts)


def _line_chart(spec: dict[str, Any], width: int, height: int) -> str:
    series = spec.get("series") or []
    categories = spec.get("categories") or []
    if not series:
        return _svg_open(width, height, spec.get("title", "")) + _svg_close()

    pad_l, pad_r, pad_t, pad_b = 50, 20, 40, 40
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b

    all_vals = [v for s in series for v in (s.get("data") or []) if v is not None]
    if not all_vals:
        return _svg_open(width, height, spec.get("title", "")) + _svg_close()
    lo, hi = min(all_vals), max(all_vals)
    span = hi - lo or 1

    parts = [_svg_open(width, height, spec.get("title", ""))]

    # grid
    for i in range(5):
        y = pad_t + plot_h * i / 4
        parts.append(
            f'<line x1="{pad_l}" y1="{y}" x2="{pad_l + plot_w}" y2="{y}" stroke="{_GRID}" stroke-width="0.5"/>'
        )

    # lines
    for si, s in enumerate(series):
        data = s.get("data") or []
        color = s.get("color") or _DEFAULT_COLORS[si % len(_DEFAULT_COLORS)]
        points = []
        for ci, v in enumerate(data):
            if v is None:
                continue
            x = pad_l + plot_w * (ci / max(1, len(data) - 1))
            y = pad_t + plot_h * (1 - (v - lo) / span)
            points.append(f"{x:.1f},{y:.1f}")
        if points:
            parts.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2"/>')
            # dots
            for pt in points:
                x, y = pt.split(",")
                parts.append(f'<circle cx="{x}" cy="{y}" r="2.5" fill="{color}"/>')

    # x labels
    for ci, cat in enumerate(categories):
        x = pad_l + plot_w * (ci / max(1, len(categories) - 1))
        y = pad_t + plot_h + 18
        parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" fill="{_TEXT_DIM}" '
            f'font-size="10" text-anchor="middle">{escape(str(cat))}</text>'
        )

    parts.append(_svg_close())
    return "\n".join(parts)


def _sparkline(spec: dict[str, Any], width: int, height: int) -> str:
    series = spec.get("series") or []
    if not series:
        return _svg_open(width, height, spec.get("title", "")) + _svg_close()

    row_h = min(40, (height - 30) // max(1, len(series)))
    parts = [_svg_open(width, height, spec.get("title", ""))]

    for si, s in enumerate(series):
        data = [v for v in (s.get("data") or []) if v is not None]
        if not data:
            continue
        color = s.get("color") or _DEFAULT_COLORS[si % len(_DEFAULT_COLORS)]
        lo, hi = min(data), max(data)
        span = hi - lo or 1
        y0 = 40 + si * row_h
        points = []
        for i, v in enumerate(data):
            x = 120 + (width - 140) * (i / max(1, len(data) - 1))
            y = y0 + row_h * 0.7 * (1 - (v - lo) / span)
            points.append(f"{x:.1f},{y:.1f}")
        parts.append(
            f'<text x="14" y="{y0 + row_h * 0.5:.0f}" fill="{_TEXT}" font-size="11">{escape(s.get("name", ""))}</text>'
        )
        parts.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="1.8"/>')

    parts.append(_svg_close())
    return "\n".join(parts)


def _pie_chart(spec: dict[str, Any], width: int, height: int) -> str:
    import math

    series = spec.get("series") or []
    categories = spec.get("categories") or []
    if not series or not series[0].get("data"):
        return _svg_open(width, height, spec.get("title", "")) + _svg_close()

    data = [v for v in (series[0]["data"] or []) if v is not None]
    if not data:
        return _svg_open(width, height, spec.get("title", "")) + _svg_close()

    cx, cy = width * 0.35, height * 0.55
    r = min(width, height) * 0.3
    total = sum(data) or 1

    parts = [_svg_open(width, height, spec.get("title", ""))]
    acc = 0.0
    for i, v in enumerate(data):
        frac = v / total
        a0 = 2 * math.pi * acc - math.pi / 2
        a1 = 2 * math.pi * (acc + frac) - math.pi / 2
        x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
        x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
        large = 1 if frac > 0.5 else 0
        color = _DEFAULT_COLORS[i % len(_DEFAULT_COLORS)]
        parts.append(
            f'<path d="M {cx:.1f} {cy:.1f} L {x0:.1f} {y0:.1f} '
            f'A {r:.1f} {r:.1f} 0 {large} 1 {x1:.1f} {y1:.1f} Z" '
            f'fill="{color}" opacity="0.85"/>'
        )
        acc += frac

    # legend
    lx = width * 0.65
    for i, cat in enumerate(categories):
        if i >= len(data):
            break
        color = _DEFAULT_COLORS[i % len(_DEFAULT_COLORS)]
        ly = 50 + i * 22
        pct = data[i] / total * 100
        parts.append(
            f'<rect x="{lx}" y="{ly - 10}" width="12" height="12" fill="{color}"/>'
            f'<text x="{lx + 18}" y="{ly}" fill="{_TEXT}" font-size="11">'
            f"{escape(str(cat))} — {pct:.1f}%</text>"
        )

    parts.append(_svg_close())
    return "\n".join(parts)


def render_svg(spec: dict[str, Any], width: int = 800, height: int = 400) -> str:
    """VizSpec dict → SVG 문자열.

    Parameters
    ----------
    spec : dict
        ChartSpec JSON.
    width, height : int
        픽셀 크기.

    Returns
    -------
    str
        `<svg>...</svg>` 문자열. 파일 저장/HTML 임베드 가능.
    """
    if spec.get("vizType") == "diagram":
        return (
            _svg_open(width, height, spec.get("title", "diagram"))
            + f'<text x="14" y="60" fill="{_TEXT_DIM}" font-size="12">'
            + f"{escape(spec.get('diagramType', ''))}: {escape(spec.get('source', '')[:200])}</text>"
            + _svg_close()
        )

    chart_type = spec.get("chartType", "")

    if chart_type == "bar":
        return _bar_chart(spec, width, height)
    if chart_type in ("line", "combo"):
        return _line_chart(spec, width, height)
    if chart_type == "sparkline":
        return _sparkline(spec, width, height)
    if chart_type == "pie":
        return _pie_chart(spec, width, height)

    # radar/waterfall/heatmap: fallback to line
    if spec.get("series"):
        return _line_chart(spec, width, height)

    # empty fallback
    return (
        _svg_open(width, height, spec.get("title", ""))
        + f'<text x="14" y="60" fill="{_TEXT_DIM}" font-size="12">'
        + f"chartType {chart_type} not supported</text>"
        + _svg_close()
    )

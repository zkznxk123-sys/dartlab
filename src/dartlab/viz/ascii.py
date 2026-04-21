"""ASCII/ANSI 터미널 차트 렌더러.

VizSpec dict → 터미널에 출력할 문자열.
plotext가 설치되어 있으면 사용, 없으면 순수 파이썬 fallback.

지원 chartType: bar, line, sparkline, combo (bar+line), pie (text summary).
radar / waterfall / heatmap — text 요약으로 fallback.
"""

from __future__ import annotations

from typing import Any

# 8색 brand 팔레트 → ANSI 256 근사
_ANSI_COLORS = {
    "#ea4647": 203,  # red
    "#fb923c": 208,  # orange
    "#3b82f6": 33,  # blue
    "#22c55e": 41,  # green
    "#8b5cf6": 135,  # purple
    "#06b6d4": 45,  # cyan
    "#f59e0b": 214,  # amber
    "#ec4899": 205,  # pink
}
_DEFAULT_ANSI = 250


def _ansi_color(hex_color: str) -> int:
    """Hex → ANSI 256 색상 코드."""
    if not hex_color:
        return _DEFAULT_ANSI
    return _ANSI_COLORS.get(hex_color.lower(), _DEFAULT_ANSI)


def _colorize(text: str, ansi_code: int) -> str:
    """ANSI 256 색상 적용."""
    return f"\033[38;5;{ansi_code}m{text}\033[0m"


def _try_plotext_bar(spec: dict[str, Any], width: int, height: int) -> str | None:
    """plotext bar chart. 설치 안 되어 있으면 None."""
    try:
        import plotext as plt
    except ImportError:
        return None
    plt.clear_figure()
    plt.theme("dark")
    plt.plotsize(width, height)
    if spec.get("title"):
        plt.title(spec["title"])
    series = spec.get("series", [])
    categories = spec.get("categories", [])
    if not series or not categories:
        return None
    # 첫 시리즈만 bar
    s = series[0]
    plt.bar(categories, s.get("data", []), label=s.get("name", ""))
    return plt.build()


def _try_plotext_line(spec: dict[str, Any], width: int, height: int) -> str | None:
    """plotext line chart."""
    try:
        import plotext as plt
    except ImportError:
        return None
    plt.clear_figure()
    plt.theme("dark")
    plt.plotsize(width, height)
    if spec.get("title"):
        plt.title(spec["title"])
    series = spec.get("series", [])
    categories = spec.get("categories", [])
    if not series:
        return None
    for s in series:
        data = [d for d in s.get("data", []) if d is not None]
        if not data:
            continue
        xs = list(range(len(data)))
        plt.plot(xs, data, label=s.get("name", ""))
    if categories:
        plt.xticks(list(range(len(categories))), categories)
    return plt.build()


def _fallback_sparkline(values: list[float | None]) -> str:
    """Unicode 블록 문자 sparkline — plotext 없이 순수 파이썬."""
    bars = "▁▂▃▄▅▆▇█"
    clean = [v for v in values if v is not None]
    if not clean:
        return "(데이터 없음)"
    lo, hi = min(clean), max(clean)
    span = hi - lo or 1
    out = []
    for v in values:
        if v is None:
            out.append(" ")
        else:
            idx = int((v - lo) / span * (len(bars) - 1))
            out.append(bars[idx])
    return "".join(out)


def _fallback_bar(spec: dict[str, Any], width: int) -> str:
    """순수 파이썬 가로 bar chart."""
    series = spec.get("series", [])
    categories = spec.get("categories", [])
    if not series or not categories:
        return "(데이터 없음)"
    s = series[0]
    data = s.get("data", [])
    color = _ansi_color(s.get("color", ""))
    max_val = max((abs(v) for v in data if v is not None), default=1) or 1
    bar_w = max(10, width - 25)

    lines = []
    if spec.get("title"):
        lines.append(spec["title"])
        lines.append("─" * min(len(spec["title"]), width))
    for cat, v in zip(categories, data):
        if v is None:
            bar = ""
            val_str = "N/A"
        else:
            n = int(abs(v) / max_val * bar_w)
            bar = _colorize("█" * n, color)
            val_str = f"{v:,.1f}" if isinstance(v, float) else f"{v:,}"
        lines.append(f"  {cat[:12]:<12} {bar} {val_str}")
    return "\n".join(lines)


def _fallback_summary(spec: dict[str, Any]) -> str:
    """지원 안 되는 차트 타입: 텍스트 요약."""
    lines = []
    if spec.get("title"):
        lines.append(f"[{spec['chartType']}] {spec['title']}")
    for s in spec.get("series", []):
        name = s.get("name", "?")
        data = s.get("data", [])
        if data:
            clean = [d for d in data if d is not None]
            if clean:
                lines.append(f"  {name}: min={min(clean):.2g} max={max(clean):.2g} last={clean[-1]:.2g}")
    return "\n".join(lines) or "(데이터 없음)"


def render_ascii(spec: dict[str, Any], width: int = 80, height: int = 20) -> str:
    """VizSpec dict → 터미널 ASCII 문자열.

    Parameters
    ----------
    spec : dict
        ChartSpec JSON (chartType, title, series, categories, options, meta).
    width, height : int
        출력 크기 (문자 단위).

    Returns
    -------
    str
        플래인/컬러 ANSI 문자열. print()로 출력 가능.
    """
    if spec.get("vizType") == "diagram":
        return f"[diagram {spec.get('diagramType', '')}]\n{spec.get('source', '')}"

    chart_type = spec.get("chartType", "")

    # plotext 우선 (bar, line)
    if chart_type == "bar":
        result = _try_plotext_bar(spec, width, height)
        if result:
            return result
        return _fallback_bar(spec, width)

    if chart_type in ("line", "combo"):
        result = _try_plotext_line(spec, width, height)
        if result:
            return result

    if chart_type == "sparkline":
        series = spec.get("series", [])
        lines = []
        if spec.get("title"):
            lines.append(spec["title"])
        for s in series:
            color = _ansi_color(s.get("color", ""))
            spark = _fallback_sparkline(s.get("data", []))
            lines.append(f"  {s.get('name', '?'):<12} {_colorize(spark, color)}")
        return "\n".join(lines)

    if chart_type == "pie":
        series = spec.get("series", [])
        categories = spec.get("categories", [])
        if series and series[0].get("data"):
            data = series[0]["data"]
            total = sum(d for d in data if d is not None) or 1
            lines = [spec.get("title", "pie")]
            for cat, v in zip(categories, data):
                if v is None:
                    continue
                pct = v / total * 100
                bar = "█" * int(pct / 2)
                lines.append(f"  {cat[:12]:<12} {bar} {pct:.1f}%")
            return "\n".join(lines)

    # 기타: 요약 fallback
    return _fallback_summary(spec)

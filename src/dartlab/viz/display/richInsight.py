"""AnalysisResult → Rich Panel 렌더링."""

from __future__ import annotations

from typing import Any

from dartlab.viz.display._tokens import AREA_LABELS as _AREA_LABELS
from dartlab.viz.display._tokens import GRADE_SCORE as _GRADE_SCORE


def _gradeBar(grade: str, width: int = 20) -> str:
    """등급 → 프로그레스 바."""
    score = _GRADE_SCORE.get(grade, 50)
    filled = int(score / 100 * width)
    empty = width - filled
    if grade in ("A",):
        color = "green"
    elif grade in ("B",):
        color = "cyan"
    elif grade in ("C",):
        color = "yellow"
    else:
        color = "red"
    bar = f"[{color}]{'█' * filled}{'░' * empty}[/{color}]"
    return f"[{grade}] {bar} {score}"


def renderInsight(result: Any) -> str:
    """AnalysisResult → Rich Panel 문자열."""
    from rich.console import Console
    from rich.panel import Panel

    lines: list[str] = []
    grades = result.grades()

    for area, grade in grades.items():
        label = _AREA_LABELS.get(area, area)
        lines.append(f"  {label:<6s} {_gradeBar(grade)}")

    anomalyCount = len(getattr(result, "anomalies", []))
    summaryLine = f"  종합: {getattr(result, 'profile', '')}"
    if anomalyCount:
        summaryLine += f"   이상치: {anomalyCount}건"
    lines.append("")
    lines.append(summaryLine)

    body = "\n".join(lines)
    corpName = getattr(result, "corpName", "")

    panel = Panel(
        body,
        title=f"[bold]{corpName} 인사이트[/bold]",
        border_style="bright_blue",
        expand=False,
        padding=(0, 1),
    )

    console = Console(record=True, width=60)
    console.print(panel)
    return console.export_text()

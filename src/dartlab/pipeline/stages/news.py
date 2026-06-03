"""News stage — 헤드라인 아카이브. 스크립트가 자체 HF push(기존 워크플로 동형)."""

from __future__ import annotations

from dartlab.pipeline.stages._runner import runScript
from dartlab.pipeline.types import PipelineMode, StageResult


def runNewsHeadlines(
    *, category: str = "news", mode: PipelineMode = "recent", codes=None, upload: bool = True, token=None
) -> StageResult:
    """뉴스 헤드라인 수집(syncNewsHeadlines 동형, 자체 HF push).

    Args:
        category: 카테고리 라벨.
        mode: 미사용.
        codes: 미사용.
        upload: 미사용(스크립트 자체 push).
        token: 미사용.

    Returns:
        StageResult.

    Raises:
        없음.

    Example:
        >>> runNewsHeadlines()  # doctest: +SKIP
        StageResult(category='news', ...)
    """
    rc = runScript(".github/scripts/sync/syncNewsHeadlines.py")
    res = StageResult(category="newsHeadlines")
    if rc != 0:
        res.report.err = 1
        res.report.failures.append(f"syncNewsHeadlines rc={rc}")
    else:
        res.report.ok = 1
    return res

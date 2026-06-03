"""EDGAR stage — sections dual-write. 스크립트가 자체 빌드+deploy(기존 워크플로 동형)."""

from __future__ import annotations

from dartlab.pipeline.stages._runner import runScript
from dartlab.pipeline.types import PipelineMode, StageResult


def runEdgarSections(
    *, category: str = "edgar", mode: PipelineMode = "recent", codes=None, upload: bool = True, token=None
) -> StageResult:
    """EDGAR sections 수집(buildEdgarSections 동형 — 10-K/10-Q fetch → docs+sections dual-write).

    Args:
        category: 카테고리 라벨.
        mode: 미사용.
        codes: 미사용.
        upload: 미사용(스크립트/deploy 경유).
        token: 미사용.

    Returns:
        StageResult.

    Raises:
        없음.

    Example:
        >>> runEdgarSections()  # doctest: +SKIP
        StageResult(category='edgar', ...)
    """
    rc = runScript(".github/scripts/sync/buildEdgarSections.py")
    res = StageResult(category="edgarSections")
    if rc != 0:
        res.report.err = 1
        res.report.failures.append(f"buildEdgarSections rc={rc}")
    else:
        res.report.ok = 1
    return res

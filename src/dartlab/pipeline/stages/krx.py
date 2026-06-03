"""KRX stage — 일별 가격 / 지수. 스크립트가 자체 HF push(기존 워크플로 동형)."""

from __future__ import annotations

from dartlab.pipeline.stages._runner import runScript
from dartlab.pipeline.types import PipelineMode, StageResult


def _run(category: str, script: str) -> StageResult:
    rc = runScript(script)
    res = StageResult(category=category)
    if rc != 0:
        res.report.err = 1
        res.report.failures.append(f"{script} rc={rc}")
    else:
        res.report.ok = 1
    return res


def runKrx(
    *, category: str = "krx", mode: PipelineMode = "recent", codes=None, upload: bool = True, token=None
) -> StageResult:
    """KRX 일별 가격 수집(buildKrxData 동형, 자체 HF push).

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
        >>> runKrx()  # doctest: +SKIP
        StageResult(category='krx', ...)
    """
    return _run("krxPrices", ".github/scripts/sync/buildKrxData.py")


def runKrxIndex(
    *, category: str = "krxIndex", mode: PipelineMode = "recent", codes=None, upload: bool = True, token=None
) -> StageResult:
    """KRX 지수 수집(buildKrxIndexData 동형, 자체 HF push).

    Args:
        category: 카테고리 라벨.
        mode: 미사용.
        codes: 미사용.
        upload: 미사용.
        token: 미사용.

    Returns:
        StageResult.

    Raises:
        없음.

    Example:
        >>> runKrxIndex()  # doctest: +SKIP
        StageResult(category='krxIndex', ...)
    """
    return _run("krxIndices", ".github/scripts/sync/buildKrxIndexData.py")

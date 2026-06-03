"""KRX stage — 일별 가격 / 지수. buildKrxData/buildKrxIndexData 동형(자체 HF push).

워크플로 호출 충실 재현: ``--mode <incremental|backfill> [--start --end] --push``.
mode·start·end 는 env(KRX_MODE/KRX_START/KRX_END)로 받는다(워크플로 github.event.inputs).
"""

from __future__ import annotations

import os

from dartlab.pipeline.stages._runner import runScript
from dartlab.pipeline.types import PipelineMode, StageResult


def _krxArgs() -> list[str]:
    mode = os.environ.get("KRX_MODE", "incremental")
    if mode == "backfill":
        return [
            "--mode",
            "backfill",
            "--start",
            os.environ.get("KRX_START", ""),
            "--end",
            os.environ.get("KRX_END", ""),
            "--push",
        ]
    return ["--mode", "incremental", "--push"]


def _run(category: str, script: str) -> StageResult:
    rc = runScript(script, *_krxArgs())
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
    """KRX 일별 가격 — buildKrxData.py --mode <…> [--start --end] --push (자체 HF push).

    Args:
        category: 카테고리 라벨.
        mode: 미사용(env KRX_MODE 우선).
        codes: 미사용.
        upload: 미사용(스크립트 --push 자체 처리).
        token: 미사용.

    Returns:
        StageResult.

    Raises:
        없음.

    Example:
        >>> runKrx()  # doctest: +SKIP
        StageResult(category='krxPrices', ...)
    """
    return _run("krxPrices", ".github/scripts/sync/buildKrxData.py")


def runKrxIndex(
    *, category: str = "krxIndex", mode: PipelineMode = "recent", codes=None, upload: bool = True, token=None
) -> StageResult:
    """KRX 지수 — buildKrxIndexData.py --mode <…> [--start --end] --push (자체 HF push).

    Args:
        category: 카테고리 라벨.
        mode: 미사용(env KRX_MODE 우선).
        codes: 미사용.
        upload: 미사용.
        token: 미사용.

    Returns:
        StageResult.

    Raises:
        없음.

    Example:
        >>> runKrxIndex()  # doctest: +SKIP
        StageResult(category='krxIndices', ...)
    """
    return _run("krxIndices", ".github/scripts/sync/buildKrxIndexData.py")

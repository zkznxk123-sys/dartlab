"""Macro stage — FRED/ECOS 거시 + cycle + regime. 세 스크립트 동형(자체 push).

워크플로 충실 재현: ``buildMacroData.py --source <source> --push`` + ``buildMacroCycle.py
--push`` + ``buildMacroRegime.py --push``. source 는 env MACRO_SOURCE(기본 all, 워크플로
github.event.inputs.source). cycle(rc2)·regime(rc3)은 서로 독립이며 둘 다 data(rc1) 성공에만
의존한다(buildMacroData 가 채운 FRED bulk 캐시 공유). cycle 실패가 regime 빌드를 막지 않는다.
"""

from __future__ import annotations

import os

from dartlab.pipeline.stages._runner import runScript
from dartlab.pipeline.types import PipelineMode, StageResult


def runMacro(
    *, category: str = "macro", mode: PipelineMode = "recent", codes=None, upload: bool = True, token=None
) -> StageResult:
    """거시지표 + cycle — buildMacroData(--source --push) + buildMacroCycle(--push).

    Args:
        category: 카테고리 라벨.
        mode: 미사용.
        codes: 미사용.
        upload: 미사용(스크립트 --push 자체 처리).
        token: 미사용.

    Returns:
        StageResult.

    Raises:
        없음.

    Example:
        >>> runMacro()  # doctest: +SKIP
        StageResult(category='macro', ...)
    """
    source = os.environ.get("MACRO_SOURCE", "all")
    rc1 = runScript(".github/scripts/sync/buildMacroData.py", "--source", source, "--push")
    rc2 = runScript(".github/scripts/sync/buildMacroCycle.py", "--push") if rc1 == 0 else 1
    rc3 = runScript(".github/scripts/sync/buildMacroRegime.py", "--push") if rc1 == 0 else 1
    res = StageResult(category="macro")
    if rc1 != 0 or rc2 != 0 or rc3 != 0:
        res.report.err = 1
        res.report.failures.append(f"macro rc=data:{rc1}/cycle:{rc2}/regime:{rc3}")
    else:
        res.report.ok = 1
    return res

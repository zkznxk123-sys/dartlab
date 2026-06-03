"""오케스트레이터 — runStage/runPipeline/listStages SSOT.

레지스트리(category→StageSpec)만 보고 dispatch. 로컬 CLI(`dartlab sync`)와 CI
(`python -m dartlab.pipeline`)가 동일하게 호출하는 단일 진입점. stage 1 개 실패가
전체 run 을 중단시키지 않게 격리(StageReport.fail 집계).
"""

from __future__ import annotations

from dartlab.pipeline.registry import RECENT_SET, buildRegistry
from dartlab.pipeline.types import PipelineMode, StageResult


def listStages() -> list[str]:
    """등록된 전 stage category 정렬 목록.

    Returns:
        category 정렬 list.

    Raises:
        없음.

    Example:
        >>> "finance" in listStages()
        True
    """
    return sorted(buildRegistry())


def describeStages() -> list[dict]:
    """전 stage 메타(`dartlab sync --list` 표시용).

    Returns:
        StageSpec.describe() dict 목록(category 정렬).

    Raises:
        없음.

    Example:
        >>> describeStages()[0].keys()  # doctest: +SKIP
        dict_keys(['category', 'online', 'uploadCategories', 'label'])
    """
    reg = buildRegistry()
    return [reg[c].describe() for c in sorted(reg)]


def runStage(
    category: str,
    *,
    mode: PipelineMode = "recent",
    codes: list[str] | None = None,
    upload: bool = True,
    token: str | None = None,
) -> StageResult:
    """단일 stage 실행 — fetch→build→upload 를 stage run 함수에 위임.

    Args:
        category: 등록된 stage category.
        mode: 수집 모드(recent/full/online 등).
        codes: 대상 코드 한정(없으면 stage 기본).
        upload: HF 업로드 수행 여부.
        token: HF 토큰(인자>env>.env).

    Returns:
        StageResult.

    Raises:
        ValueError: 미등록 category.
        NotImplementedError: run 미구현 stage.

    Example:
        >>> runStage("finance", upload=False)  # doctest: +SKIP
        StageResult(category='finance', ...)
    """
    reg = buildRegistry()
    if category not in reg:
        raise ValueError(f"unknown stage '{category}' — 등록: {sorted(reg)}")
    spec = reg[category]
    if spec.run is None:
        raise NotImplementedError(f"stage '{category}' run 미구현")
    return spec.run(category=category, mode=mode, codes=codes, upload=upload, token=token)


def runPipeline(
    categories: list[str] | None = None,
    *,
    mode: PipelineMode = "recent",
    upload: bool = True,
) -> dict[str, StageResult]:
    """여러 stage 순차 실행 — 1 개 실패가 나머지 중단 X(격리).

    Args:
        categories: 실행할 category 목록(없으면 RECENT_SET).
        mode: 수집 모드.
        upload: HF 업로드 여부.

    Returns:
        {category: StageResult} dict.

    Raises:
        없음 (개별 stage 예외는 StageResult.report.fail 로 격리).

    Example:
        >>> runPipeline(["finance"], upload=False)  # doctest: +SKIP
        {'finance': StageResult(...)}
    """
    cats = list(categories) if categories else list(RECENT_SET)
    results: dict[str, StageResult] = {}
    for c in cats:
        try:
            results[c] = runStage(c, mode=mode, upload=upload)
        except Exception as exc:  # noqa: BLE001 — stage 격리: 1 개 실패가 전체 중단 X
            res = StageResult(category=c)
            res.report.fail = 1
            res.report.failures.append(f"{type(exc).__name__}: {exc}")
            print(f"[pipeline] stage '{c}' 실패(격리): {type(exc).__name__}: {exc}", flush=True)
            results[c] = res
    return results

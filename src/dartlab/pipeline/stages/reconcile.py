"""reconcile stages — 로컬 ↔ HF 양방향 동기화(panel·edgarPanel), 운영자 트리거.

forward stage(dartZip/edgarPanel)가 *변경분만* push 한다면, 본 stage 는 로컬·HF 전 파일을
집합 비교해 부족분만 양쪽으로 채운다(``reconcileCategory``). ⚠ ephemeral CI runner 에선
pull 이 전량 재다운로드라 무의미 — 영속 로컬 store(운영자 머신)용. allFilings 는 별도
``allFilingsReconcile`` stage(``_meta`` 의미론).
"""

from __future__ import annotations

from dartlab.pipeline.types import PipelineMode, StageResult


def _runReconcile(stageCat: str, dataCat: str, *, upload: bool, token: str | None) -> StageResult:
    """공통 reconcile stage 본체 — ``reconcileCategory`` 호출 + StageResult 매핑."""
    from dartlab.pipeline.reconcile import reconcileCategory

    res = StageResult(category=stageCat)
    try:
        s = reconcileCategory(dataCat, pull=True, push=upload, token=token)
        res.rows = int(s["pulled"])
        res.uploaded = int(s["pushed"])
        res.report.ok = 1
        print(
            f"[pipeline] {stageCat}: 로컬 {s['localBefore']} · HF {s['remoteBefore']} "
            f"· pull {s['pulled']} · push {s['pushed']} · inSync={s['inSync']}",
            flush=True,
        )
    except Exception as exc:  # noqa: BLE001 — reconcile 실패 격리(다음 호출 자연 회복)
        res.report.err = 1
        res.report.failures.append(f"{stageCat}: {type(exc).__name__}: {exc}")
        print(f"[pipeline] {stageCat} 실패(격리): {exc}", flush=True)
    return res


def runPanelReconcile(
    *,
    category: str = "panelReconcile",
    mode: PipelineMode = "incremental",
    codes: list[str] | None = None,
    upload: bool = True,
    token: str | None = None,
) -> StageResult:
    """DART panel 로컬 ↔ HF 양방향 reconcile stage (운영자 트리거).

    Args:
        category: 미사용("panelReconcile" 고정).
        mode: 미사용.
        codes: 미사용(전 파일 집합 비교).
        upload: False 면 push 끔(pull-only).
        token: HF 토큰.

    Returns:
        StageResult (rows=pull 종목수, uploaded=push 종목수).

    Raises:
        없음 (reconcile 예외는 StageResult 로 격리).

    Example:
        >>> runPanelReconcile(upload=False)  # doctest: +SKIP
        StageResult(category='panelReconcile', ...)
    """
    return _runReconcile("panelReconcile", "panel", upload=upload, token=token)


def runEdgarPanelReconcile(
    *,
    category: str = "edgarPanelReconcile",
    mode: PipelineMode = "incremental",
    codes: list[str] | None = None,
    upload: bool = True,
    token: str | None = None,
) -> StageResult:
    """EDGAR panel 로컬 ↔ HF 양방향 reconcile stage (운영자 트리거).

    Args:
        category: 미사용("edgarPanelReconcile" 고정).
        mode: 미사용.
        codes: 미사용(전 파일 집합 비교).
        upload: False 면 push 끔(pull-only).
        token: HF 토큰.

    Returns:
        StageResult (rows=pull 티커수, uploaded=push 티커수).

    Raises:
        없음 (reconcile 예외는 StageResult 로 격리).

    Example:
        >>> runEdgarPanelReconcile(upload=False)  # doctest: +SKIP
        StageResult(category='edgarPanelReconcile', ...)
    """
    return _runReconcile("edgarPanelReconcile", "edgarPanel", upload=upload, token=token)

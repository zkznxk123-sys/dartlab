"""allFilings stage — 비정기 공시 **일별** parquet forward 증분 (recent N days).

원본=SSOT 전략([[project_original_ssot_strategy]]): allFilings 는 원본 zip 보관 안 함 —
``collectMetaRange``+``fillContent`` 로 **일자별** parquet(``data/dart/allFilings/{date}.parquet``,
``{date}``=YYYYMMDD)만 유지. 일자가 immutable 키라 윈도가 월 경계를 넘어도 손상 0(각 날짜 독립
파일). 정기보고서(사업/분기/반기)는 ``report_nm`` 으로 자동 제외 → docs(정기 zip) 와 중복 0.
``pushAllFilings`` 가 자체 HF 업로드(``_meta`` 제외, dart/allFilings 단일 소유 = 본 stage —
searchIndexDelta 의 옛 이중 push 제거됨). lookback 일수는 ``SYNC_LOOKBACK_DAYS`` env(기본 7)
또는 ``DART_ALLFILINGS_LOOKBACK``.
"""

from __future__ import annotations

import os
from datetime import date, timedelta

from dartlab.pipeline.types import PipelineMode, StageResult


def _recentDates(days: int) -> list[str]:
    """오늘 포함 최근 ``days`` 일의 YYYYMMDD 리스트(최신→과거)."""
    today = date.today()
    return [(today - timedelta(days=i)).strftime("%Y%m%d") for i in range(days)]


def runAllFilings(
    *,
    category: str = "allFilings",
    mode: PipelineMode = "incremental",
    codes: list[str] | None = None,
    upload: bool = True,
    token: str | None = None,
) -> StageResult:
    """allFilings 비정기 공시 forward 증분 수집 → 월별 parquet + HF push.

    Args:
        category: 미사용("allFilings" 고정).
        mode: 미사용(incremental 고정).
        codes: 미사용(날짜 윈도 기반).
        upload: HF 업로드(``pushAllFilings``) 여부.
        token: HF 토큰.

    Returns:
        StageResult (rows=수집 본문 행수, uploaded=push 한 일자수).

    Raises:
        없음 (수집/업로드 예외는 StageResult 로 격리).

    Example:
        >>> runAllFilings(upload=False)  # doctest: +SKIP
        StageResult(category='allFilings', ...)
    """
    from dartlab.gather.dart.allFilingsCollector import collectMetaRange, fillContent
    from dartlab.gather.dart.allFilingsSync import pushAllFilings

    days = int(os.environ.get("SYNC_LOOKBACK_DAYS") or os.environ.get("DART_ALLFILINGS_LOOKBACK") or "7")
    dates = _recentDates(days)
    start, end = dates[-1], dates[0]
    res = StageResult(category="allFilings")

    try:
        collectMetaRange(start, end, showProgress=False)
        rows = 0
        for d in dates:
            df = fillContent(d, showProgress=False)
            if df is not None:
                rows += df.height
        res.rows = rows
        res.report.ok = 1
    except Exception as exc:  # noqa: BLE001 — 수집 실패 격리(다음 sync 자연 회복)
        res.report.err = 1
        res.report.failures.append(f"allFilings collect {start}~{end}: {type(exc).__name__}: {exc}")
        print(f"[pipeline] allFilings 수집 실패(격리): {exc}", flush=True)
        return res

    if upload:
        try:
            pushAllFilings(dates, token=token)
            res.uploaded = len(dates)
        except Exception as exc:  # noqa: BLE001 — 업로드 실패 격리
            res.report.fail = 1
            res.report.failures.append(f"allFilings push: {type(exc).__name__}: {exc}")
            print(f"[pipeline] allFilings push 실패(격리): {exc}", flush=True)
    return res


def runAllFilingsReconcile(
    *,
    category: str = "allFilingsReconcile",
    mode: PipelineMode = "incremental",
    codes: list[str] | None = None,
    upload: bool = True,
    token: str | None = None,
) -> StageResult:
    """allFilings 로컬 ↔ HF **양방향 reconcile** stage (운영자 트리거).

    forward 증분(``runAllFilings``)이 최근 N일만 본다면, 본 stage 는 로컬·HF 전 일자를
    집합 비교해 부족분만 양쪽으로 채운다(``reconcileAllFilings``): HF 가 앞선 일자는
    로컬로 pull, 로컬이 앞선 일자는 HF 로 push. 월 단위 백필 후 또는 머신/CI 간 동기화에
    쓴다. ⚠ ephemeral CI runner 에서 부르면 pull 이 전 이력 재다운로드라 무의미 —
    영속 로컬 store(운영자 머신)용. daily 최신화는 ``originalSync.yml`` allfilings job 이 담당.

    Args:
        category: 미사용("allFilingsReconcile" 고정).
        mode: 미사용.
        codes: 미사용(전 일자 집합 비교).
        upload: False 면 push 방향 끔(pull-only reconcile).
        token: HF 토큰.

    Returns:
        StageResult (rows=pull 한 일자수, uploaded=push 한 일자수).

    Raises:
        없음 (reconcile 예외는 StageResult 로 격리).

    Example:
        >>> runAllFilingsReconcile(upload=False)  # doctest: +SKIP
        StageResult(category='allFilingsReconcile', ...)
    """
    from dartlab.gather.dart.allFilingsSync import reconcileAllFilings

    res = StageResult(category="allFilingsReconcile")
    try:
        summary = reconcileAllFilings(pull=True, push=upload, token=token)
        res.rows = int(summary["pulled"])
        res.uploaded = int(summary["pushed"])
        res.report.ok = 1
        print(
            f"[pipeline] allFilings reconcile: 로컬 {summary['localBefore']}→{summary['localAfter']}일, "
            f"HF {summary['remoteBefore']}일 · pull {summary['pulled']} · push {summary['pushed']}"
            f" · inSync={summary['inSync']}",
            flush=True,
        )
    except Exception as exc:  # noqa: BLE001 — reconcile 실패 격리(다음 호출 자연 회복)
        res.report.err = 1
        res.report.failures.append(f"allFilings reconcile: {type(exc).__name__}: {exc}")
        print(f"[pipeline] allFilings reconcile 실패(격리): {exc}", flush=True)
    return res

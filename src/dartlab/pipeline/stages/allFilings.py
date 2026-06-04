"""allFilings stage — 비정기 공시 월별 parquet forward 증분 (recent N days).

원본=SSOT 전략([[project_original_ssot_strategy]]): allFilings 는 원본 zip 보관 안 함 —
``collectMetaRange``+``fillContent`` 로 일자별 parquet(``data/dart/allFilings/{date}.parquet``)
만 유지. 정기보고서(사업/분기/반기)는 ``report_nm`` 으로 자동 제외 → docs(정기 zip) 와 중복 0.
``pushAllFilings`` 가 자체 HF 업로드(``_meta`` 제외). lookback 일수는 ``SYNC_LOOKBACK_DAYS``
env(기본 7) 또는 ``DART_ALLFILINGS_LOOKBACK``.
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
    from dartlab.gather.dart.allFilingsCollector import collectMetaRange, fillContent, pushAllFilings

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

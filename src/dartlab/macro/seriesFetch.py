"""macro 엔진 공통 헬퍼."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import polars as pl

log = logging.getLogger(__name__)


def recentTimeseries(df, months: int = 6, valueCol: str = "value") -> list[dict] | None:
    """gather DataFrame에서 최근 N개월분 시계열 추출.

    Parameters
    ----------
    df : pl.DataFrame | None
        gather.macro() 결과 (date, value 컬럼).
    months : int
        추출 기간 (개월).
    value_col : str
        값 컬럼명.

    Returns
    -------
    list[dict] | None
        [{date: str — "YYYY-MM-DD", value: float}] 리스트. 데이터 없으면 None.
    """
    if df is None or len(df) == 0:
        return None
    try:
        cutoff = datetime.now() - timedelta(days=months * 30)
        filtered = df.filter(df["date"] >= cutoff).sort("date")
        if len(filtered) == 0:
            return None
        dates = filtered.get_column("date").to_list()
        vals = filtered.get_column(valueCol).to_list()
        return [
            {"date": str(d)[:10], "value": float(v) if v is not None else None}
            for d, v in zip(dates, vals)
            if v is not None
        ]
    except (KeyError, ValueError, TypeError):
        return None


def applyAsOf(df, asOf: str | None) -> "pl.DataFrame | None":
    """as_of 날짜까지만 필터링 — 백테스트용.

    Parameters
    ----------
    df : pl.DataFrame | None
        date 컬럼을 포함한 시계열 DataFrame.
    as_of : str | None
        기준 날짜 ("YYYY-MM-DD"). None이면 필터 없이 원본 반환.

    Returns
    -------
    pl.DataFrame | None
        as_of 이하 행만 남긴 DataFrame. df가 None이면 None.
    """
    if asOf is None or df is None or len(df) == 0:
        return df
    try:
        cutoff = datetime.strptime(asOf, "%Y-%m-%d").date() if isinstance(asOf, str) else asOf
        return df.filter(df["date"] <= cutoff)
    except (ValueError, TypeError):
        return df


def applyOverrides(data: dict, overrides: dict | None) -> dict:
    """overrides dict를 data에 병합 — 시나리오 시뮬레이션용.

    Parameters
    ----------
    data : dict
        원본 데이터 dict.
    overrides : dict | None
        덮어쓸 키-값 쌍. None이면 원본 그대로.

    Returns
    -------
    dict
        overrides가 병합된 data (in-place 수정).
    """
    if overrides:
        data.update(overrides)
    return data


# ══════════════════════════════════════
# 공통 fetch 헬퍼 — 90회 중복 제거
# ══════════════════════════════════════


def getGather(asOf: str | None = None) -> "Any":
    """gather 인스턴스 생성 — as_of 있으면 자동 필터링 래핑.

    모든 L2 모듈의 _fetch_* 함수에서 이것을 사용.

    Parameters
    ----------
    as_of : str | None
        백테스트 기준 날짜 ("YYYY-MM-DD"). None이면 원본 gather.

    Returns
    -------
    Gather
        macro() 호출 시 as_of 필터가 적용된 gather 인스턴스.
    """
    from dartlab.core.di import getMacroProvider

    g = getMacroProvider().getDefaultGather()
    if asOf is None:
        return g

    _orig = g.macro

    def _filtered(sid):
        return applyAsOf(_orig(sid), asOf)

    import copy

    gc = copy.copy(g)
    gc.macro = _filtered  # type: ignore
    return gc


def fetchLatest(g, seriesId: str) -> float | None:
    """시리즈의 최신값 1개 조회.

    Parameters
    ----------
    g : Gather
        gather 인스턴스 (get_gather() 결과).
    series_id : str
        FRED/ECOS 시리즈 ID (예: "GDP", "UNRATE").

    Returns
    -------
    float | None
        최신 관측값. 실패 시 None (debug 로깅).
    """
    try:
        df = g.macro(seriesId)
        if df is not None and len(df) > 0:
            vals = df.get_column("value").drop_nulls()
            if len(vals) > 0:
                return float(vals[-1])
    except (KeyError, ValueError, TypeError, AttributeError) as e:
        log.debug("fetch_latest(%s) 실패: %s", seriesId, e)
    return None


def fetchLatestWithPrev(g, seriesId: str) -> tuple[float | None, float | None]:
    """최신값 + 직전값 조회 — 모멘텀 계산용.

    Parameters
    ----------
    g : Gather
        gather 인스턴스.
    series_id : str
        시리즈 ID.

    Returns
    -------
    tuple[float | None, float | None]
        (최신값, 직전값). 데이터 부족 시 (None, None).
    """
    try:
        df = g.macro(seriesId)
        if df is not None and len(df) > 0:
            vals = df.get_column("value").drop_nulls()
            if len(vals) >= 2:
                return float(vals[-1]), float(vals[-2])
            if len(vals) == 1:
                return float(vals[-1]), None
    except (KeyError, ValueError, TypeError, AttributeError) as e:
        log.debug("fetch_latest_with_prev(%s) 실패: %s", seriesId, e)
    return None, None


def fetchSeriesList(g, seriesId: str) -> list[float] | None:
    """전체 시계열을 float 리스트로 조회.

    Parameters
    ----------
    g : Gather
        gather 인스턴스.
    series_id : str
        시리즈 ID.

    Returns
    -------
    list[float] | None
        시간순 값 리스트. Hamilton/Sahm/FCI 등 시계열 알고리즘에 사용.
        데이터 없으면 None.
    """
    try:
        df = g.macro(seriesId)
        if df is not None and len(df) > 0:
            vals = df.get_column("value").drop_nulls().to_list()
            if vals:
                return [float(v) for v in vals]
    except (KeyError, ValueError, TypeError, AttributeError) as e:
        log.debug("fetch_series_list(%s) 실패: %s", seriesId, e)
    return None


def fetchYoy(g, seriesId: str) -> float | None:
    """12개월 전 대비 YoY 변화율.

    Parameters
    ----------
    g : Gather
        gather 인스턴스.
    series_id : str
        시리즈 ID.

    Returns
    -------
    float | None
        전년동월대비 변화율 (%). 관측치 13개 미만이면 None.
    """
    try:
        df = g.macro(seriesId)
        if df is not None and len(df) > 0:
            vals = df.get_column("value").drop_nulls()
            if len(vals) >= 13:
                current = float(vals[-1])
                prev = float(vals[-13])
                if prev != 0:
                    return ((current - prev) / abs(prev)) * 100
    except (KeyError, ValueError, TypeError, AttributeError) as e:
        log.debug("fetch_yoy(%s) 실패: %s", seriesId, e)
    return None


def fetchChangePct(g, seriesId: str, lookback: int = 63) -> float | None:
    """lookback 관측치 전 대비 변화율.

    Parameters
    ----------
    g : Gather
        gather 인스턴스.
    series_id : str
        시리즈 ID.
    lookback : int
        비교 기준 관측치 수. 기본 63 ≈ 3개월(일간 데이터).

    Returns
    -------
    float | None
        변화율 (%). 데이터 부족 시 None.
    """
    try:
        df = g.macro(seriesId)
        if df is not None and len(df) > 0:
            vals = df.get_column("value").drop_nulls()
            if len(vals) > lookback:
                current = float(vals[-1])
                old = float(vals[-lookback])
                if old != 0:
                    return ((current - old) / abs(old)) * 100
    except (KeyError, ValueError, TypeError, AttributeError) as e:
        log.debug("fetch_change_pct(%s) 실패: %s", seriesId, e)
    return None


def fetchWithHistory(g, seriesId: str) -> dict[str, float | None]:
    """최신 + 직전 + 6개월전 값을 한 번에 조회.

    Parameters
    ----------
    g : Gather
        gather 인스턴스.
    series_id : str
        시리즈 ID.

    Returns
    -------
    dict[str, float | None]
        current : float | None — 최신값
        prev : float | None — 직전값
        6m : float | None — 6개월전 값
    """
    result: dict[str, float | None] = {}
    try:
        df = g.macro(seriesId)
        if df is not None and len(df) > 0:
            vals = df.get_column("value").drop_nulls().to_list()
            if vals:
                result["current"] = float(vals[-1])
                if len(vals) > 1:
                    result["prev"] = float(vals[-2])
                if len(vals) > 6:
                    result["6m"] = float(vals[-7])
    except (KeyError, ValueError, TypeError, AttributeError) as e:
        log.debug("fetch_with_history(%s) 실패: %s", seriesId, e)
    return result


def fetchMonthlyDict(g, seriesId: str) -> dict[str, float] | None:
    """시리즈를 월간 dict로 변환 — 역사적 분석용.

    같은 달에 여러 값이면 마지막 값.

    Parameters
    ----------
    g : Gather
        gather 인스턴스.
    series_id : str
        시리즈 ID.

    Returns
    -------
    dict[str, float] | None
        {"YYYY-MM": value} 매핑. 데이터 없으면 None.
    """
    try:
        df = g.macro(seriesId)
        if df is None or len(df) == 0:
            return None
        dates = df.get_column("date").to_list()
        values = df.get_column("value").to_list()
        monthly: dict[str, float] = {}
        for d, v in zip(dates, values):
            if v is not None:
                monthly[str(d)[:7]] = float(v)
        return monthly if monthly else None
    except (KeyError, ValueError, TypeError, AttributeError) as e:
        log.debug("fetch_monthly_dict(%s) 실패: %s", seriesId, e)
        return None


def collectTimeseries(g, seriesMap: dict[str, str]) -> dict[str, list[dict] | None]:
    """여러 시리즈의 최근 시계열을 일괄 수집.

    Parameters
    ----------
    g : Gather
        gather 인스턴스.
    series_map : dict[str, str]
        {라벨: 시리즈ID} 매핑 (예: {"GDP": "GDP", "실업률": "UNRATE"}).

    Returns
    -------
    dict[str, list[dict] | None]
        {라벨: [{date: str, value: float}] | None} — 실패한 시리즈는 None.
    """
    ts: dict[str, list[dict] | None] = {}
    for label, sid in seriesMap.items():
        try:
            ts[label] = recentTimeseries(g.macro(sid))
        except (KeyError, ValueError, TypeError, AttributeError):
            ts[label] = None
    return ts

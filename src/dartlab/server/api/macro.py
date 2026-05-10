"""FRED 매크로 경제지표 API 엔드포인트."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Query

router = APIRouter()


def _getFred():
    """Fred 인스턴스 생성 — API 키 없으면 503."""
    from dartlab.gather.fred import Fred
    from dartlab.gather.fred.types import AuthenticationError

    try:
        return Fred()
    except AuthenticationError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


def _toRecords(df):
    """Polars DataFrame → list[dict] (JSON serializable)."""
    if df.is_empty():
        return []
    return df.to_dicts()


# ── 시계열 ──


@router.get("/api/fred/series/{series_id}")
async def apiFredSeries(
    seriesId: str,
    start: str | None = Query(None),
    end: str | None = Query(None),
    frequency: str | None = Query(None),
    transform: str = Query("raw"),
    window: int = Query(12),
):
    """FRED 시계열 조회 + 변환."""
    from dartlab.gather.fred.types import FredError

    f = _getFred()
    try:
        if transform == "yoy":
            df = await asyncio.to_thread(f.yoy, seriesId, start=start, end=end)
        elif transform == "mom":
            df = await asyncio.to_thread(f.mom, seriesId, start=start, end=end)
        elif transform == "ma":
            df = await asyncio.to_thread(f.movingAverage, seriesId, window=window, start=start, end=end)
        else:
            df = await asyncio.to_thread(f.series, seriesId, start=start, end=end, frequency=frequency)
    except FredError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    meta = await asyncio.to_thread(f.meta, seriesId)
    return {
        "meta": {
            "id": meta.id,
            "title": meta.title,
            "frequency": meta.frequency,
            "units": meta.units,
        },
        "data": _toRecords(df),
    }


# ── 검색 ──


@router.get("/api/fred/search")
async def apiFredSearch(
    q: str = Query(...),
    limit: int = Query(20),
):
    """FRED 시리즈 검색."""
    from dartlab.gather.fred.types import FredError

    f = _getFred()
    try:
        df = await asyncio.to_thread(f.search, q, limit=limit)
    except FredError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"results": _toRecords(df)}


# ── 비교 ──


@router.get("/api/fred/compare")
async def apiFredCompare(
    ids: str = Query(..., description="콤마 구분 시리즈 ID"),
    start: str | None = Query(None),
    end: str | None = Query(None),
    normalizeTo: str | None = Query(None),
):
    """복수 시계열 비교."""
    from dartlab.gather.fred import transform as _transform
    from dartlab.gather.fred.types import FredError

    seriesIds = [s.strip() for s in ids.split(",") if s.strip()]
    if len(seriesIds) < 2:
        raise HTTPException(status_code=400, detail="시리즈 ID 2개 이상 필요")

    f = _getFred()
    try:
        df = await asyncio.to_thread(f.compare, seriesIds, start=start, end=end)
    except FredError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if normalizeTo:
        df = _transform.normalizeMulti(df, baseDate=normalizeTo)

    return {"data": _toRecords(df)}


# ── 카탈로그 ──


@router.get("/api/fred/catalog")
async def apiFredCatalog(
    group: str | None = Query(None),
):
    """주요 경제지표 카탈로그."""
    from dartlab.gather.fred.catalog import getGroups, toDataframe

    if group and group not in getGroups():
        raise HTTPException(status_code=400, detail=f"그룹 없음. 사용 가능: {', '.join(getGroups())}")

    df = toDataframe(group)
    return {"catalog": _toRecords(df)}


# ── 상관분석 ──


@router.get("/api/fred/correlation")
async def apiFredCorrelation(
    ids: str = Query(..., description="콤마 구분 시리즈 ID"),
    start: str | None = Query(None),
    end: str | None = Query(None),
    maxLag: int = Query(12),
    leadLag: str | None = Query(None, description="선행/후행 분석 쌍 (콤마 구분 2개)"),
):
    """시계열 상관분석 + 선행/후행."""
    from dartlab.gather.fred.types import FredError

    seriesIds = [s.strip() for s in ids.split(",") if s.strip()]
    if len(seriesIds) < 2:
        raise HTTPException(status_code=400, detail="시리즈 ID 2개 이상 필요")

    f = _getFred()
    result: dict = {}

    try:
        corr = await asyncio.to_thread(f.correlation, seriesIds, start=start, end=end)
        result["correlation"] = _toRecords(corr)
    except FredError as exc:
        result["correlation_error"] = str(exc)

    if leadLag:
        pair = [s.strip() for s in leadLag.split(",") if s.strip()]
        if len(pair) == 2:
            try:
                ll = await asyncio.to_thread(
                    f.leadLag,
                    pair[0],
                    pair[1],
                    maxLag=maxLag,
                    start=start,
                    end=end,
                )
                result["lead_lag"] = _toRecords(ll)
            except FredError as exc:
                result["lead_lag_error"] = str(exc)

    return result

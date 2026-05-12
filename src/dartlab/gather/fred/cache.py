"""FRED 시계열 캐시 — core/cache/TimeseriesCache 위임."""

from __future__ import annotations

from typing import Any

from dartlab.core.cache import TimeseriesCache

_cache = TimeseriesCache(ttlDaily=6 * 3600, ttlOther=24 * 3600)


def get(seriesId: str, start: str | None, end: str | None, freq: str | None, aggregation: str | None) -> Any | None:
    """캐시 조회. TTL 만료 시 None.

    Parameters
    ----------
    series_id : str — FRED 시리즈 ID (예: "GDP", "UNRATE").
    start : str | None — 조회 시작일.
    end : str | None — 조회 종료일.
    freq : str | None — 주기 ("d"/"w"/"m"/"q"/"a").
    aggregation : str | None — 집계 방법 ("avg"/"sum"/"eop").

    Returns
    -------
    Any | None
        캐시된 시계열. TTL 만료/미캐시 시 None.

    Raises
    ------
    없음
        키 부재는 None 반환.

    Example
    -------
    >>> v = get("GDP", "2020-01-01", "2024-12-31", "q", "avg")
    """
    return _cache.get(seriesId, start, end, freq, aggregation)


def put(
    seriesId: str,
    start: str | None,
    end: str | None,
    freq: str | None,
    aggregation: str | None,
    value: Any,
    *,
    daily: bool = False,
) -> None:
    """캐시 저장. daily=True 면 TTL 6시간, 아니면 24시간.

    Parameters
    ----------
    seriesId : str
        FRED 시리즈 ID.
    start, end, freq, aggregation : str | None
        캐시 키 구성요소 — fetch 인자와 동일.
    value : Any
        저장할 시계열 값.
    daily : bool
        ``True`` 면 6시간 TTL (일별 데이터용), ``False`` 면 24시간.

    Returns
    -------
    None

    Raises
    ------
    없음
        TimeseriesCache.put 내부 오류는 흡수.

    Example
    -------
    >>> put("GDP", "2020-01-01", "2024-12-31", "q", "avg", df)
    """
    _cache.put(value, seriesId, start, end, freq, aggregation, daily=daily)


def clear() -> None:
    """FRED 캐시 전체 비우기.

    Returns
    -------
    None

    Raises
    ------
    없음.

    Example
    -------
    >>> clear()
    """
    _cache.clear()

"""ECOS 시계열 캐시 — core/cache/TimeseriesCache 위임."""

from __future__ import annotations

from typing import Any

from dartlab.core.cache import TimeseriesCache

_cache = TimeseriesCache(ttlDaily=6 * 3600, ttlOther=24 * 3600)


def get(indicatorId: str, start: str | None, end: str | None) -> Any | None:
    """캐시 조회. TTL 만료 시 None.

    Parameters
    ----------
    indicatorId : str — ECOS 카탈로그 지표 ID (예: "GDP", "CPI").
    start : str | None — 조회 시작일.
    end : str | None — 조회 종료일.

    Returns
    -------
    Any | None
        캐시된 시계열 값. TTL 만료 또는 미캐시 시 None.

    Raises
    ------
    없음
        키 부재는 None 반환.

    Example
    -------
    >>> v = get("GDP", "2020-01-01", "2024-12-31")
    """
    return _cache.get(indicatorId, start, end)


def put(
    indicatorId: str,
    start: str | None,
    end: str | None,
    value: Any,
    *,
    daily: bool = False,
) -> None:
    """캐시 저장. daily=True 면 TTL 6시간, 아니면 24시간.

    Parameters
    ----------
    indicatorId : str
        ECOS 카탈로그 지표 ID.
    start, end : str | None
        조회 범위 — 캐시 키의 일부.
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
        ``TimeseriesCache.put`` 위임 — 내부 오류는 흡수.

    Example
    -------
    >>> put("GDP", "2020-01-01", "2024-12-31", df)
    """
    _cache.put(value, indicatorId, start, end, daily=daily)


def clear() -> None:
    """ECOS 캐시 전체 비우기.

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

"""FRED 시계열 캐시 — core/cache/TimeseriesCache 위임."""

from __future__ import annotations

from typing import Any

from dartlab.core.cache import TimeseriesCache

_cache = TimeseriesCache(ttl_daily=6 * 3600, ttl_other=24 * 3600)


def get(
    series_id: str, start: str | None, end: str | None, frequency: str | None, aggregation: str | None
) -> Any | None:
    """캐시 조회. TTL 만료 시 None.

    Parameters
    ----------
    series_id : str — FRED 시리즈 ID (예: "GDP", "UNRATE").
    start : str | None — 조회 시작일.
    end : str | None — 조회 종료일.
    frequency : str | None — 주기 ("d"/"w"/"m"/"q"/"a").
    aggregation : str | None — 집계 방법 ("avg"/"sum"/"eop").
    """
    return _cache.get(series_id, start, end, frequency, aggregation)


def put(
    series_id: str,
    start: str | None,
    end: str | None,
    frequency: str | None,
    aggregation: str | None,
    value: Any,
    *,
    daily: bool = False,
) -> None:
    """캐시 저장. daily=True 면 TTL 6시간, 아니면 24시간."""
    _cache.put(value, series_id, start, end, frequency, aggregation, daily=daily)


def clear() -> None:
    """FRED 캐시 전체 비우기."""
    _cache.clear()

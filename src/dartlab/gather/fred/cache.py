"""FRED 시계열 캐시 — core/cache/TimeseriesCache 위임."""

from __future__ import annotations

from typing import Any

from dartlab.core.cache import TimeseriesCache

_cache = TimeseriesCache(ttlDaily=6 * 3600, ttlOther=24 * 3600)


def get(seriesId: str, start: str | None, end: str | None, freq: str | None, aggregation: str | None) -> Any | None:
    """캐시 조회. TTL 만료 시 None.

    Capabilities: TimeseriesCache.get 위임 — (seriesId, start, end, freq, aggregation) 키.
    AIContext: FRED API 호출 직전 캐시 hit 확인 — rate limit 회피 + 응답 속도 ↑.
    Guide: TTL daily=6h / other=24h. 만료 시 None — caller 가 fetch.
    When: series.fetchSeries / facade 호출의 첫 단계.
    How: ``_cache.get(seriesId, start, end, freq, aggregation)`` direct.

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

    Requires
    --------
    core.cache.TimeseriesCache 가용.

    Example
    -------
    >>> v = get("GDP", "2020-01-01", "2024-12-31", "q", "avg")

    See Also
    --------
    put : 동행 write.
    clear : 전체 invalidate.
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

    Capabilities: TimeseriesCache.put 위임 — daily 분기로 TTL 차별화.
    AIContext: FRED fetch 직후 저장 — 후속 동일 호출의 latency 감소.
    Guide: daily 시리즈만 짧은 TTL (6h). 분기/연간은 24h 충분.
    When: fetchSeries / facade 결과 cache 저장 시.
    How: ``_cache.put(value, seriesId, start, end, freq, aggregation, daily=daily)``.

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

    Requires
    --------
    core.cache.TimeseriesCache 가용.

    Example
    -------
    >>> put("GDP", "2020-01-01", "2024-12-31", "q", "avg", df)

    See Also
    --------
    get : 동행 read.
    """
    _cache.put(value, seriesId, start, end, freq, aggregation, daily=daily)


def clear() -> None:
    """FRED 캐시 전체 비우기.

    Capabilities: TimeseriesCache.clear 위임 — 모든 cached 시리즈 제거.
    AIContext: 사용자가 최신 FRED 데이터 강제 / 테스트 isolation 시 진입.
    Guide: 모든 seriesId 영향 — 비싸진 cache 재구축 비용 인지.
    When: 데이터 freshness 강제 / 테스트 fixture / 디버깅 시.
    How: ``_cache.clear()`` direct.

    Returns
    -------
    None

    Raises
    ------
    없음.

    Requires
    --------
    core.cache.TimeseriesCache 가용.

    Example
    -------
    >>> clear()

    See Also
    --------
    get · put : 영향 받는 cache operation.
    """
    _cache.clear()

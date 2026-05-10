"""시계열 데이터 공용 TTL 캐시 — BoundedCache 기반.

FRED/ECOS 등 외부 시계열 provider 가 공유하는 MD5 해시 키 + TTL 엔트리 구조.
각 provider 는 `TimeseriesCache(ttl_daily=..., ttl_other=...)` 인스턴스 하나만 소유.

사용법::

    from dartlab.core.cache import TimeseriesCache

    _cache = TimeseriesCache(ttl_daily=6 * 3600, ttl_other=24 * 3600)

    val = _cache.get(series_id, start, end, frequency)
    if val is None:
        val = fetch_from_api(...)
        _cache.put(val, series_id, start, end, frequency, daily=(frequency == "d"))
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

from dartlab.core.memory import BoundedCache


def makeKey(*parts: Any) -> str:
    """캐시 키 생성 — 인자들을 파이프로 연결 후 MD5 해시.

    Parameters
    ----------
    *parts : Any
        키 구성 요소 (임의 개수, 순서 의존).

    Returns
    -------
    str
        32자리 MD5 해시 문자열.
    """
    raw = "|".join(str(p) for p in parts)
    return hashlib.md5(raw.encode()).hexdigest()


class TimeseriesCache:
    """시계열 데이터 TTL 캐시 (daily/other 2-tier).

    BoundedCache 를 내부 저장소로 사용하여 메모리 안전성 보장.
    엔트리 포맷: ``(timestamp_monotonic, ttl_seconds, value)``.

    Parameters
    ----------
    ttl_daily : int
        일별 데이터 TTL (초). 예: 6 * 3600 (6시간).
    ttl_other : int
        월별/분기별 등 데이터 TTL (초). 예: 24 * 3600 (24시간).
    max_entries : int
        BoundedCache 최대 엔트리 수. 기본 256.
    """

    __slots__ = ("_cache", "_ttl_daily", "_ttl_other")

    def __init__(self, *, ttlDaily: int, ttlOther: int, maxEntries: int = 256):
        self._cache = BoundedCache(maxEntries=maxEntries)
        self._ttl_daily = ttlDaily
        self._ttl_other = ttlOther

    def get(self, *parts: Any) -> Any | None:
        """캐시 조회. TTL 만료 시 자동 삭제 후 None 반환.

        Parameters
        ----------
        *parts : Any
            키 구성 요소 — put 시 전달한 순서·값과 동일해야 hit.

        Returns
        -------
        Any | None
            캐시된 값. 미스·만료 시 None.
        """
        key = makeKey(*parts)
        entry = self._cache.get(key)
        if entry is None:
            return None
        ts, ttl, value = entry
        if time.monotonic() - ts > ttl:
            self._cache.pop(key, None)
            return None
        return value

    def put(self, value: Any, *parts: Any, daily: bool = False) -> None:
        """캐시 저장.

        Parameters
        ----------
        value : Any
            저장할 값 (보통 pl.DataFrame).
        *parts : Any
            키 구성 요소.
        daily : bool
            True 면 ttl_daily, False 면 ttl_other 적용.
        """
        key = makeKey(*parts)
        ttl = self._ttl_daily if daily else self._ttl_other
        self._cache[key] = (time.monotonic(), ttl, value)

    def clear(self) -> None:
        """캐시 전체 비우기."""
        self._cache.clear()

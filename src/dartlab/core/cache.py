"""시계열 데이터 공용 TTL 캐시."""

from __future__ import annotations

import hashlib
import time
from typing import Any

from dartlab.core.memory import BoundedCache


def makeKey(*parts: Any) -> str:
    """캐시 키 생성 — 인자들을 파이프로 연결 후 MD5 해시."""
    raw = "|".join(str(p) for p in parts)
    return hashlib.md5(raw.encode()).hexdigest()


class TimeseriesCache:
    """시계열 데이터 TTL 캐시 (daily/other 2-tier)."""

    __slots__ = ("_cache", "_ttl_daily", "_ttl_other")

    def __init__(self, *, ttlDaily: int, ttlOther: int, maxEntries: int = 256):
        self._cache = BoundedCache(maxEntries=maxEntries)
        self._ttl_daily = ttlDaily
        self._ttl_other = ttlOther

    def get(self, *parts: Any) -> Any | None:
        """캐시 조회. TTL 만료 시 자동 삭제 후 None 반환."""
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
        """캐시 저장."""
        key = makeKey(*parts)
        ttl = self._ttl_daily if daily else self._ttl_other
        self._cache[key] = (time.monotonic(), ttl, value)

    def clear(self) -> None:
        """캐시 전체 비우기."""
        self._cache.clear()


__all__ = ["TimeseriesCache", "makeKey"]

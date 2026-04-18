"""FRED 시계열 캐시 — BoundedCache 기반 메모리 안전."""

from __future__ import annotations

import hashlib
import time
from typing import Any

from dartlab.core.memory import BoundedCache

# TTL (초)
_TTL_DAILY = 6 * 3600  # 일별 데이터: 6시간
_TTL_OTHER = 24 * 3600  # 월별/분기별: 24시간

_cache = BoundedCache(max_entries=256)


def _make_key(*parts: Any) -> str:
    """캐시 키 생성 — 인자들을 파이프로 연결 후 MD5 해시.

    Parameters
    ----------
    *parts : Any
        키 구성 요소 (series_id, start, end, frequency, aggregation 등).

    Returns
    -------
    str
        32자리 MD5 해시 문자열.
    """
    raw = "|".join(str(p) for p in parts)
    return hashlib.md5(raw.encode()).hexdigest()


def get(
    series_id: str, start: str | None, end: str | None, frequency: str | None, aggregation: str | None
) -> Any | None:
    """캐시 조회. TTL 만료 시 자동 삭제 후 None 반환.

    Parameters
    ----------
    series_id : str
        FRED 시리즈 ID (예: "GDP", "UNRATE").
    start : str | None
        조회 시작일.
    end : str | None
        조회 종료일.
    frequency : str | None
        주기 ("d"/"w"/"m"/"q"/"a").
    aggregation : str | None
        집계 방법 ("avg"/"sum"/"eop").

    Returns
    -------
    Any | None
        캐시된 값 (보통 pl.DataFrame). 미스 또는 TTL 만료 시 None.
    """
    key = _make_key(series_id, start, end, frequency, aggregation)
    entry = _cache.get(key)
    if entry is None:
        return None
    ts, ttl, value = entry
    if time.monotonic() - ts > ttl:
        _cache.pop(key, None)
        return None
    return value


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
    """캐시 저장. daily=True 면 TTL 6시간, 아니면 24시간.

    Parameters
    ----------
    series_id : str
        FRED 시리즈 ID.
    start : str | None
        조회 시작일.
    end : str | None
        조회 종료일.
    frequency : str | None
        주기.
    aggregation : str | None
        집계 방법.
    value : Any
        저장할 값 (보통 pl.DataFrame).
    daily : bool
        True 면 TTL 6시간 (일별 데이터용), False 면 24시간.
    """
    key = _make_key(series_id, start, end, frequency, aggregation)
    ttl = _TTL_DAILY if daily else _TTL_OTHER
    _cache[key] = (time.monotonic(), ttl, value)


def clear() -> None:
    """FRED 메모리 캐시 전체 비우기. BoundedCache 엔트리 모두 삭제.

    Returns
    -------
    None
    """
    _cache.clear()

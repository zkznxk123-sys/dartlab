"""시계열 데이터 공용 TTL 캐시."""

from __future__ import annotations

import hashlib
import time
from typing import Any

from dartlab.core.memory import BoundedCache


def makeKey(*parts: Any) -> str:
    """캐시 키 생성 — 인자들을 파이프로 연결 후 MD5 해시.

    Capabilities:
        임의 인자 조합을 BoundedCache key로 쓸 수 있는 짧은 문자열로 정규화한다.
    AIContext:
        FRED/ECOS 같은 gather 시계열 캐시가 동일한 호출 인자를 같은 key로 묶는 L0
        helper다.
    Guide:
        충돌 위험이 완전히 0인 식별자가 필요한 곳에는 쓰지 않는다. 캐시 key 전용이다.
    When:
        URL, series id, query 옵션처럼 여러 인자를 하나의 cache key로 합칠 때.
    How:
        각 part를 str로 변환하고 pipe로 연결한 뒤 MD5 hex digest를 반환한다.
    Requires:
        모든 part가 의미 있는 ``str(part)`` 표현을 가져야 한다.
    Raises:
        str(part) 변환 중 발생한 예외를 그대로 전달한다.
    Args:
        *parts: cache key에 포함할 임의 값들.
    Returns:
        32자 MD5 hex digest 문자열.
    Example:
        >>> makeKey("GDP", "fred") == makeKey("GDP", "fred")
        True
    SeeAlso:
        TimeseriesCache.get: 동일 key 생성 방식으로 캐시를 조회한다.
        TimeseriesCache.put: 동일 key 생성 방식으로 값을 저장한다.
    """
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
        """캐시 조회. TTL 만료 시 자동 삭제 후 None 반환.

        Capabilities:
            makeKey 기반 key 조회와 TTL 만료 정리를 한 번에 수행한다.
        AIContext:
            gather source가 원격 시계열을 반복 요청하지 않도록 process-local cache를
            확인하는 표준 경로다.
        Guide:
            반환값 None은 미스와 저장된 None을 구분하지 않는다. None을 값으로 캐싱하지
            않는 호출자에 적합하다.
        When:
            네트워크 fetch 전에 같은 인자로 저장된 시계열 DataFrame이나 dict가 있는지 볼 때.
        How:
            BoundedCache에서 entry를 꺼내 monotonic 시간 기준 TTL을 넘으면 삭제한다.
        Requires:
            put이 같은 parts 조합으로 값을 저장했어야 hit가 가능하다.
        Raises:
            str(part) 변환 중 발생한 예외를 그대로 전달한다.
        Args:
            *parts: makeKey에 전달할 cache key 구성 요소.
        Returns:
            저장된 값 또는 cache miss/TTL 만료 시 None.
        Example:
            >>> c = TimeseriesCache(ttlDaily=60, ttlOther=60)
            >>> c.put("value", "GDP")
            >>> c.get("GDP")
            'value'
        SeeAlso:
            put: TTL과 함께 값을 저장한다.
            clear: 캐시 전체를 비운다.
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

        Capabilities:
            daily/other TTL tier 중 하나를 골라 값을 process-local BoundedCache에 저장한다.
        AIContext:
            macro/gather 원격 source 응답을 일정 시간 재사용해 분석 호출의 속도와 안정성을
            높인다.
        Guide:
            daily=True는 일 단위로 갱신되는 데이터, 기본값은 더 짧은 일반 TTL에 사용한다.
        When:
            원격 fetch 또는 비싼 변환 결과를 성공적으로 얻은 직후.
        How:
            makeKey(parts)와 현재 monotonic timestamp, 선택된 ttl, value를 tuple로 저장한다.
        Requires:
            value는 BoundedCache에 저장 가능한 Python 객체여야 한다.
        Raises:
            str(part) 변환 중 발생한 예외를 그대로 전달한다.
        Args:
            value: 캐시에 저장할 객체.
            *parts: makeKey에 전달할 cache key 구성 요소.
            daily: True면 ttlDaily, False면 ttlOther를 적용한다.
        Returns:
            None.
        Example:
            >>> c = TimeseriesCache(ttlDaily=60, ttlOther=1)
            >>> c.put({"v": 1}, "series", daily=True)
        SeeAlso:
            get: 저장된 값을 TTL 검증 후 조회한다.
            makeKey: key 생성 규칙.
        """
        key = makeKey(*parts)
        ttl = self._ttl_daily if daily else self._ttl_other
        self._cache[key] = (time.monotonic(), ttl, value)

    def clear(self) -> None:
        """캐시 전체 비우기.

        Capabilities:
            TimeseriesCache 내부 BoundedCache 항목을 모두 제거한다.
        AIContext:
            테스트, 데이터 갱신, 사용자가 stale cache를 의심하는 상황에서 process-local
            시계열 캐시를 초기화한다.
        Guide:
            디스크 캐시는 지우지 않는다. 메모리 TTL cache만 비운다.
        When:
            테스트 setup/teardown 또는 원격 데이터 갱신 직후.
        How:
            내부 BoundedCache.clear를 호출한다.
        Requires:
            없음.
        Raises:
            없음.
        Returns:
            None.
        Example:
            >>> c = TimeseriesCache(ttlDaily=60, ttlOther=60)
            >>> c.clear()
        SeeAlso:
            get: clear 후에는 같은 key가 None을 반환한다.
        """
        self._cache.clear()


__all__ = ["TimeseriesCache", "makeKey"]

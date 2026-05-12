"""Gather 엔진 telemetry — emit 채널 표준화 (G+ P-Q5.1).

per-axis latency, cache hit/miss, circuit breaker fallback 같은 운영 신호를
일관된 key 로 ``core.messaging.emit`` 에 흘려보낸다. 외부 listener 없으면
no-op (emit 자체가 listener 부재 시 print 만). 본 모듈은 dispatch hook 용
얇은 wrapper — 호출자가 ``with`` 블록 / decorator 없이 직접 호출.

Capabilities:
    - emitGatherFetch(axis, latencyMs, *, cacheHit, market) — fetch 종료 신호
    - emitGatherCacheStats(hit, miss, evicted) — 캐시 상태 스냅샷
    - emitGatherFallback(axis, primary, fallback) — fallback chain 발동
    - 모듈-level counter (hit/miss/evicted) — 누적 집계

AIContext:
    - SRE/관측 도구가 ``[gather]`` prefix 로그 로 latency 분포 도출
    - circuit breaker 동작 감사 (어떤 source 가 자주 떨어지는지)

Guide:
    핵심은 emit() 의 key 라벨. ``gather:fetch:done`` / ``gather:cache:stats``
    / ``gather:fallback`` 3 채널. 외부 listener (logging/prometheus) 가
    이 key 를 subscribe 해서 메트릭화.

When:
    mixin price/flow/macro/news 같은 fetch 진입 후. cache get/put 직후.
    circuit breaker 의 fallback 진입 시.

How:
    fetch 함수::

        t0 = time.monotonic()
        cacheHit = False
        try:
            result = cache.get(key)
            if result is not None:
                cacheHit = True
                return result
            result = client.fetch(...)
            cache.put(key, result)
            return result
        finally:
            emitGatherFetch("price", (time.monotonic() - t0) * 1000, cacheHit=cacheHit, market="KR")

Requires:
    ``dartlab.core.messaging.emit`` — listener 없을 때 no-op print.

Raises:
    없음 — telemetry 는 ``try/except`` 로 감싸진 fire-and-forget.

Example::

    from dartlab.gather.infra.telemetry import emitGatherFetch
    emitGatherFetch("price", 132.5, cacheHit=False, market="KR")
    # → "[dartlab] gather:fetch:done axis=price latencyMs=132.5 cacheHit=False market=KR"

See Also:
    ``dartlab.core.messaging.emit`` — backend.
    ``dartlab.gather.infra.cache.GatherCache`` — hit/miss 호출자.
    ``dartlab.gather.infra.resilience.CircuitBreaker`` — fallback 호출자.
"""

from __future__ import annotations

import threading
from typing import Final

from dartlab.core.messaging import emit as _coreEmit

# 모듈-level 누적 카운터 (process-local). thread-safe.
_lock: Final[threading.Lock] = threading.Lock()
_cacheHits: int = 0
_cacheMisses: int = 0
_cacheEvictions: int = 0

# 매 N record 마다 emit 트리거 (busy emit 회피).
_EMIT_EVERY: Final[int] = 100


def emitGatherFetch(axis: str, latencyMs: float, *, cacheHit: bool, market: str | None = None) -> None:
    """fetch 종료 신호 — axis × latency × cacheHit (× market).

    Capabilities:
        - latency 분포 도출 (axis 별, market 별)
        - cache hit rate 자동 집계 (외부 listener 가 카운트)

    AIContext:
        - 느린 fetch 진단 — DARTLAB_TELEMETRY env 가 stdout listener 활성화 시
          stdout 으로 latency 직접 출력

    Guide:
        모든 mixin/sources 의 fetch 진입 후 finally 블록에서 호출.
        try/except 로 자체 보호 — telemetry 실패가 본 로직 깨지 않음.

    When:
        매 fetch 종료 직후. cache hit 의 경우 cacheHit=True 로 신호.

    How:
        try:
            fetch...
        finally:
            emitGatherFetch(axis, (time.monotonic() - t0) * 1000, cacheHit=False)

    Args:
        axis: gather axis 이름 (예: "price"/"flow"/"macro").
        latencyMs: 측정 latency (ms).
        cacheHit: cache hit 였으면 True.
        market: 시장 (선택). None 이면 외부 listener 가 axis default 가정.

    Returns:
        None — fire-and-forget.

    Requires:
        ``dartlab.core.messaging.emit`` — listener 없으면 print only.

    Raises:
        없음 — 내부 try/except 흡수.

    Example::

        emitGatherFetch("price", 132.5, cacheHit=False, market="KR")

    See Also:
        ``emitGatherCacheStats`` — 캐시 상태 스냅샷.
    """
    try:
        _coreEmit(
            "gather:fetch:done",
            axis=axis,
            latencyMs=round(latencyMs, 2),
            cacheHit=cacheHit,
            market=market or "default",
        )
    except (KeyError, ValueError, RuntimeError):
        pass


def emitGatherCacheStats(hit: int, miss: int, evicted: int) -> None:
    """캐시 상태 스냅샷 — 누적 hit/miss/evicted 카운터.

    Capabilities:
        - 캐시 hit rate 추적 (hit / (hit + miss))
        - eviction 발생률 — BoundedCache 크기 조정 단서

    AIContext:
        - SRE 가 cache hit rate 모니터링 — 너무 낮으면 TTL 조정 또는 cache 크기 ↑

    Guide:
        호출 시점은 GatherCache 의 evict 이벤트 또는 주기적 (예: 매 100 호출).
        emit 시점에 모듈-level 카운터도 갱신.

    When:
        GatherCache.evict() 후 또는 디버그 dump 시.

    How:
        emitGatherCacheStats(hit, miss, evicted) — 인자 자체가 누적 값.

    Args:
        hit: 누적 cache hit 수.
        miss: 누적 cache miss 수.
        evicted: 누적 eviction 수.

    Returns:
        None.

    Requires:
        모듈 전역 카운터 (thread-safe lock).

    Raises:
        없음 — try/except 흡수.

    Example::

        emitGatherCacheStats(hit=1200, miss=180, evicted=45)

    See Also:
        ``emitGatherFetch`` — fetch 별 cacheHit 신호.
    """
    global _cacheHits, _cacheMisses, _cacheEvictions
    try:
        with _lock:
            _cacheHits = hit
            _cacheMisses = miss
            _cacheEvictions = evicted
        _coreEmit("gather:cache:stats", hit=hit, miss=miss, evicted=evicted)
    except (KeyError, ValueError, RuntimeError):
        pass


def emitGatherFallback(axis: str, primary: str, fallback: str) -> None:
    """circuit breaker fallback 발동 — primary 실패 → fallback 사용.

    Capabilities:
        - source 안정성 추적 (primary 가 자주 떨어지는지)
        - fallback chain 동작 감사

    AIContext:
        - infra 가 primary source 의 health 도구 ↔ 본 신호로 자동 대응

    Guide:
        sources/* 모듈의 fallback dispatch 시 호출. CircuitBreaker 가
        fallback 으로 전환할 때마다 신호.

    When:
        primary fetch 실패 후 fallback 호출 직전.

    How:
        try:
            primaryFetch(...)
        except SourceUnavailableError:
            emitGatherFallback("price", "naver", "yahoo")
            return fallbackFetch(...)

    Args:
        axis: gather axis 이름.
        primary: primary source 이름 (예: "naver").
        fallback: 전환된 fallback source 이름 (예: "yahoo").

    Returns:
        None.

    Requires:
        ``dartlab.core.messaging.emit``.

    Raises:
        없음.

    Example::

        emitGatherFallback("price", primary="naver", fallback="yahoo")

    See Also:
        ``dartlab.gather.infra.resilience.CircuitBreaker`` — fallback 결정.
    """
    try:
        _coreEmit("gather:fallback", axis=axis, primary=primary, fallback=fallback)
    except (KeyError, ValueError, RuntimeError):
        pass


def recordCacheHit() -> None:
    """캐시 hit 1회 누적 — 매 _EMIT_EVERY 회마다 자동 snapshot emit.

    Capabilities:
        - GatherCache.get 의 hit 분기에서 fire-and-forget 호출.
        - 매 N=100 hit 마다 emit 으로 외부 listener 에 누적 신호.

    AIContext:
        - cache hit rate 자동 추적 — listener 가 hit / (hit+miss) 비율 계산.

    Guide:
        호출 시점은 GatherCache.get 의 hit 직후. 본 함수가 lock + N 트리거 책임.

    When:
        매 캐시 hit 직후.

    How:
        ``recordCacheHit()`` — 인자 없음, 1 회 증가.

    Args:
        없음.

    Returns:
        None — fire-and-forget.

    Requires:
        모듈 전역 lock + 카운터.

    Raises:
        없음 — try/except 흡수.

    Example::

        recordCacheHit()  # cache.py 의 get hit 직후

    See Also:
        ``recordCacheMiss`` / ``recordCacheEvict`` / ``getCacheStatsSnapshot``.
    """
    global _cacheHits
    try:
        with _lock:
            _cacheHits += 1
            shouldEmit = _cacheHits % _EMIT_EVERY == 0
            hit, miss, evicted = _cacheHits, _cacheMisses, _cacheEvictions
        if shouldEmit:
            _coreEmit("gather:cache:stats", hit=hit, miss=miss, evicted=evicted)
    except (KeyError, ValueError, RuntimeError):
        pass


def recordCacheMiss() -> None:
    """캐시 miss 1회 누적 — 매 _EMIT_EVERY 회마다 자동 snapshot emit.

    Capabilities:
        - GatherCache.get 의 miss 분기에서 fire-and-forget 호출.

    AIContext:
        - cache miss 폭증 감지 (예: TTL 설정 잘못, 새 stockCode 폭주).

    Guide:
        호출 시점은 GatherCache.get 이 None 반환 시 (entry 미존재 또는 TTL 만료).

    When:
        매 캐시 miss 직후.

    How:
        ``recordCacheMiss()``.

    Args:
        없음.

    Returns:
        None.

    Requires:
        모듈 전역 lock + 카운터.

    Raises:
        없음.

    Example::

        recordCacheMiss()

    See Also:
        ``recordCacheHit`` / ``recordCacheEvict``.
    """
    global _cacheMisses
    try:
        with _lock:
            _cacheMisses += 1
            shouldEmit = _cacheMisses % _EMIT_EVERY == 0
            hit, miss, evicted = _cacheHits, _cacheMisses, _cacheEvictions
        if shouldEmit:
            _coreEmit("gather:cache:stats", hit=hit, miss=miss, evicted=evicted)
    except (KeyError, ValueError, RuntimeError):
        pass


def recordCacheEvict() -> None:
    """캐시 eviction 1회 누적 — 매 _EMIT_EVERY 회마다 자동 snapshot emit.

    Capabilities:
        - GatherCache.put 의 LRU 축출 분기에서 호출.

    AIContext:
        - eviction 빈발 감지 → cache maxEntries ↑ 필요 신호.

    Guide:
        capacity overflow 시 가장 오래된 항목 제거 직후 호출.

    When:
        매 LRU 축출 직후.

    How:
        ``recordCacheEvict()``.

    Args:
        없음.

    Returns:
        None.

    Requires:
        모듈 전역 lock + 카운터.

    Raises:
        없음.

    Example::

        recordCacheEvict()

    See Also:
        ``recordCacheHit`` / ``recordCacheMiss``.
    """
    global _cacheEvictions
    try:
        with _lock:
            _cacheEvictions += 1
            shouldEmit = _cacheEvictions % _EMIT_EVERY == 0
            hit, miss, evicted = _cacheHits, _cacheMisses, _cacheEvictions
        if shouldEmit:
            _coreEmit("gather:cache:stats", hit=hit, miss=miss, evicted=evicted)
    except (KeyError, ValueError, RuntimeError):
        pass


def resetCacheStats() -> None:
    """테스트용 카운터 리셋 — 단위 테스트 격리 보장.

    Capabilities:
        - 모듈 전역 카운터를 0 으로 초기화.

    AIContext:
        - test fixture 의 setup/teardown 에서 호출 — counter 누수 회피.

    Guide:
        프로덕션 코드에서 호출 금지. 테스트 전용.

    When:
        pytest fixture teardown 또는 setup.

    How:
        ``resetCacheStats()``.

    Args:
        없음.

    Returns:
        None.

    Requires:
        모듈 전역 lock.

    Raises:
        없음.

    Example::

        resetCacheStats()

    See Also:
        ``getCacheStatsSnapshot``.
    """
    global _cacheHits, _cacheMisses, _cacheEvictions
    with _lock:
        _cacheHits = 0
        _cacheMisses = 0
        _cacheEvictions = 0


def getCacheStatsSnapshot() -> dict[str, int]:
    """현재 누적 카운터 dict 반환 (테스트/디버깅).

    Capabilities:
        - emit 채널 없이도 직접 stat 접근 (process-local).

    AIContext:
        - 단위 테스트에서 emitGatherCacheStats 호출 검증.

    Guide:
        프로세스 전 hit/miss/evicted 합산만 반환. 별도 reset 함수 별도.

    When:
        디버깅 / 테스트 / 시작 직후 sanity check.

    How:
        ``snap = getCacheStatsSnapshot()`` → ``snap["hit"]`` 등 조회.

    Args:
        없음.

    Returns:
        ``{"hit": int, "miss": int, "evicted": int}``.

    Requires:
        모듈 전역 카운터 (thread-safe lock 보호 read).

    Raises:
        없음.

    Example::

        snap = getCacheStatsSnapshot()
        assert snap["hit"] >= 0

    See Also:
        ``emitGatherCacheStats`` — 카운터 갱신.
    """
    with _lock:
        return {"hit": _cacheHits, "miss": _cacheMisses, "evicted": _cacheEvictions}

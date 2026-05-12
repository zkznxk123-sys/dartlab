"""주가 fallback facade — 시장별 동적 fallback + circuit breaker + health tracking (async)."""

from __future__ import annotations

import copy
import logging
import time

from ..domains import getPriceFallback, loadDomain
from ..infra.cache import GatherCache
from ..infra.resilience import circuitBreaker, healthTracker
from ..marketConfig import getMarketConfig
from ..types import GatherError, PriceSnapshot

log = logging.getLogger(__name__)

# 모듈 레벨 stale cache (price.py 단독 사용 시)
_stale_cache = GatherCache(maxEntries=100)


async def fetch(
    stockCode: str,
    *,
    market: str = "KR",
    client=None,
    limit: int | None = None,
) -> PriceSnapshot | None:
    """주가 — 시장별 fallback 체인 + circuit breaker + health scoring (async).

    1. health score로 fallback 순서 재정렬
    2. circuit open인 소스 skip
    3. 성공/실패를 circuit breaker + health tracker에 기록
    4. 전부 실패 시 stale cache에서 반환 시도

    Parameters
    ----------
    stock_code : str
        종목코드/티커 (예: "005930", "AAPL").
    market : str
        시장 코드 ("KR", "US", "JP" 등). 기본 "KR".
    client : httpx.AsyncClient | None
        HTTP 클라이언트. None이면 GatherHttpClient 자동 생성.
    limit : int | None
        단건 스냅샷 반환 함수라 무시된다. 인터페이스 호환 목적으로만 존재.

    Returns
    -------
    PriceSnapshot | None
        주가 스냅샷. 주요 필드:

        - current : float — 현재가 (원 또는 해당 통화)
        - change : float — 전일 대비 변동 (원)
        - change_pct : float — 전일 대비 변동률 (%)
        - high_52w : float — 52주 최고가 (원)
        - low_52w : float — 52주 최저가 (원)
        - volume : int — 거래량 (주)
        - market_cap : float — 시가총액 (억원)
        - per : float | None — PER (배)
        - pbr : float | None — PBR (배)
        - dividend_yield : float | None — 배당수익률 (%)
        - currency : str — 통화 코드 ("KRW", "USD" 등)
        - is_stale : bool — stale cache 반환 여부

        전체 fallback + stale cache 모두 실패 시 None.
    """
    config = getMarketConfig(market)
    chain = getPriceFallback(market)
    chain = healthTracker.reorder(chain)

    # client=None이면 자체 생성
    if client is None:
        from ..infra.http import GatherHttpClient

        client = GatherHttpClient()

    for source_name in chain:
        if circuitBreaker.isOpen(source_name):
            log.debug("price skip %s (circuit open)", source_name)
            continue

        t0 = time.monotonic()
        try:
            module = loadDomain(source_name)
            if not hasattr(module, "fetchPrice"):
                continue

            result = await module.fetchPrice(stockCode, client, market=market)

            latency = time.monotonic() - t0

            if result:
                result.currency = config.currency
                result.market = market
                circuitBreaker.recordSuccess(source_name)
                healthTracker.record(source_name, success=True, latency=latency)
                # stale cache에도 저장 (fallback용)
                _stale_cache.putTyped(stockCode, "price", result)
                return result

            # None 반환 = 데이터 없음 (에러는 아님)
            healthTracker.record(source_name, success=True, latency=latency)

        except (GatherError, ImportError, OSError) as exc:
            latency = time.monotonic() - t0
            circuitBreaker.recordFailure(source_name)
            healthTracker.record(source_name, success=False, latency=latency)
            log.debug("price fallback %s 실패: %s", source_name, exc)
            continue

    # 모든 소스 실패 → stale cache 시도
    stale = _stale_cache.getTyped(stockCode, "price", allowStale=True)
    if stale is not None and isinstance(stale, PriceSnapshot):
        stale_copy = copy.copy(stale)
        stale_copy.is_stale = True
        log.info("price %s: stale cache 반환", stockCode)
        return stale_copy

    return None

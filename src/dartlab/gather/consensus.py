"""컨센서스 fallback facade — 시장별 다중 소스 + stale cache."""

from __future__ import annotations

import logging
import time

from .domains import CONSENSUS_FALLBACK, load_domain
from .resilience import circuit_breaker as _cb
from .types import ConsensusData, GatherError

log = logging.getLogger(__name__)

# ── stale-while-revalidate 캐시 ──
_CACHE_TTL = 3600  # 1시간 fresh
_STALE_TTL = 86400  # 24시간 stale 허용
_cache: dict[str, tuple[ConsensusData, float]] = {}


async def fetch(
    stock_code: str,
    *,
    market: str = "KR",
    client=None,
) -> ConsensusData | None:
    """컨센서스 — fallback 체인 (async) + stale-while-revalidate.

    KR: naver → naver_global
    US/기타: naver_global

    모든 소스 실패 시 24시간 이내 stale 캐시를 반환한다.

    Parameters
    ----------
    stock_code : str
        종목코드 ("005930") 또는 티커 ("AAPL").
    market : str
        "KR" 또는 "US". 기본 "KR".
    client : GatherHttpClient | None
        HTTP 클라이언트. None이면 도메인 모듈 기본값 사용.

    Returns
    -------
    ConsensusData | None
        targetPrice : float — 목표 주가 (원 또는 USD).
        recommendation : str — 투자의견 ("Buy", "Hold" 등).
        numAnalysts : int — 분석 애널리스트 수 (명).
        source : str — 데이터 출처 도메인명.
        None — 모든 소스 실패 + stale 만료(24시간 초과) 시.
    """
    cacheKey = f"{market}:{stock_code}"
    now = time.monotonic()

    # fresh 캐시 히트
    if cacheKey in _cache:
        data, ts = _cache[cacheKey]
        if now - ts < _CACHE_TTL:
            return data

    if market == "KR":
        chain = CONSENSUS_FALLBACK  # ["naver", "naver_global"]
    else:
        chain = ["naver_global"]  # US는 naver 불가

    for domain_name in chain:
        if _cb.is_open(domain_name):
            log.debug("consensus skip %s (circuit open)", domain_name)
            continue
        try:
            module = load_domain(domain_name)
            if not hasattr(module, "fetch_consensus"):
                continue
            if domain_name == "naver":
                result = await module.fetch_consensus(stock_code, client)
            else:
                result = await module.fetch_consensus(stock_code, client, market=market)
            if result:
                _cb.record_success(domain_name)
                _cache[cacheKey] = (result, now)
                return result
        except (GatherError, ImportError, OSError, AttributeError) as exc:
            _cb.record_failure(domain_name)
            log.debug("consensus fallback %s 실패: %s", domain_name, exc)
            continue

    # 모든 소스 실패 → stale 캐시 반환
    if cacheKey in _cache:
        data, ts = _cache[cacheKey]
        if now - ts < _STALE_TTL:
            log.warning("consensus stale cache 사용: %s (%.0f초 전)", cacheKey, now - ts)
            return data

    return None

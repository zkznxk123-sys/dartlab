"""히스토리 fallback facade — naver(KR) → naver_global → fmp 순서 (async)."""

from __future__ import annotations

import logging

from ..domains import HISTORY_FALLBACK, loadDomain
from ..infra.resilience import circuitBreaker
from ..types import GatherError

log = logging.getLogger(__name__)


async def fetch(
    stockCode: str,
    *,
    start: str,
    end: str,
    market: str = "KR",
    client=None,
) -> list[dict]:
    """히스토리 OHLCV — fallback 체인 (async).

    Parameters
    ----------
    stock_code : str
        종목코드/티커 (예: "005930", "AAPL").
    start : str
        조회 시작일 (ISO 형식, 예: "2024-01-01").
    end : str
        조회 종료일 (ISO 형식, 예: "2024-12-31").
    market : str
        시장 코드 ("KR", "US" 등). 기본 "KR".
    client : httpx.AsyncClient | None
        HTTP 클라이언트. None이면 GatherHttpClient 자동 생성.

    Returns
    -------
    list[dict]
        일별 OHLCV 리스트. 각 dict 키:

        - date : str — 거래일 (YYYY-MM-DD)
        - open : float — 시가 (원 또는 해당 통화)
        - high : float — 고가 (원)
        - low : float — 저가 (원)
        - close : float — 종가 (원)
        - volume : int — 거래량 (주)

        전체 fallback 실패 시 빈 리스트 [].
    """
    chain: list[str] = []
    # KR → naver 최우선
    if market == "KR":
        chain.append("naver")
    chain.extend(HISTORY_FALLBACK)
    if "fmp" not in chain:
        chain.append("fmp")
    # 중복 제거 (순서 유지)
    seen: set[str] = set()
    chain = [s for s in chain if not (s in seen or seen.add(s))]  # type: ignore[func-returns-value]

    # client=None이면 자체 생성 (price.py와 동일 패턴)
    if client is None:
        from ..infra.http import GatherHttpClient

        client = GatherHttpClient()

    for source_name in chain:
        if circuitBreaker.isOpen(source_name):
            continue

        try:
            module = loadDomain(source_name)

            if hasattr(module, "fetchHistory"):
                result = await module.fetchHistory(
                    stockCode,
                    client,
                    start=start,
                    end=end,
                    market=market,
                )
                if result:
                    return result

        except (GatherError, ImportError, OSError, ValueError, AttributeError) as exc:
            log.debug("history fallback %s 실패: %s", source_name, exc)
            continue

    return []

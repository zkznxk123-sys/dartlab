"""수급 fallback facade — 한국 전용 (naver)."""

from __future__ import annotations

import logging

from .domains import FLOW_FALLBACK, load_domain
from .types import GatherError

log = logging.getLogger(__name__)


async def fetch(
    stock_code: str,
    *,
    market: str = "KR",
    client=None,
) -> list[dict] | None:
    """수급 시계열 — fallback 체인 (async). KR만 지원.

    Parameters
    ----------
    stock_code : str
        종목코드 (예: "005930").
    market : str
        시장 코드. "KR"만 지원, 그 외 None 반환.
    client : httpx.AsyncClient | None
        HTTP 클라이언트. None이면 도메인 내부에서 생성.

    Returns
    -------
    list[dict] | None
        수급 시계열 리스트. 각 dict 키:

        - date : str — 거래일 (YYYY-MM-DD)
        - foreignNet : float — 외국인 순매수 (주)
        - institutionNet : float — 기관 순매수 (주)
        - individualNet : float — 개인 순매수 (주)

        KR 외 시장이거나 전체 fallback 실패 시 None.
    """
    if market != "KR":
        return None

    for domain_name in FLOW_FALLBACK:
        try:
            module = load_domain(domain_name)
            result = await module.fetch_flow(stock_code, client)
            if result:
                return result
        except (GatherError, ImportError, OSError) as exc:
            log.debug("flow fallback %s 실패: %s", domain_name, exc)
            continue
    return None

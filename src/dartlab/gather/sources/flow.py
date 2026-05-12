"""수급 fallback facade — 한국 전용 (naver)."""

from __future__ import annotations

import logging

from ..domains import FLOW_FALLBACK, loadDomain
from ..types import GatherError

log = logging.getLogger(__name__)


async def fetch(
    stockCode: str,
    *,
    market: str = "KR",
    client=None,
    limit: int | None = None,
) -> list[dict] | None:
    """수급 시계열 — fallback 체인 (async). KR만 지원.

    Capabilities:
        - FLOW_FALLBACK 체인 순차 시도 (Naver → 다음)
        - 첫 성공 source 결과 반환

    AIContext:
        - mixin.flow 의 backend — KR 수급 axis 의 source-level 진입점

    Guide:
        market 인자가 "KR" 외이면 None. provider 가 KR 한정.

    When:
        gather.flow() 호출 시 (lazy fallback chain).

    How:
        FLOW_FALLBACK 의 도메인 순서대로 호출 → 첫 성공 결과 .

    Parameters
    ----------
    stock_code : str
        종목코드 (예: "005930").
    market : str
        시장 코드. "KR"만 지원, 그 외 None 반환.
    client : httpx.AsyncClient | None
        HTTP 클라이언트. None이면 도메인 내부에서 생성.
    limit : int | None
        반환 행수 상한 (가장 최근 N개). None이면 전체.

    Returns
    -------
    list[dict] | None
        수급 시계열 리스트. 각 dict 키:

        - date : str — 거래일 (YYYY-MM-DD)
        - foreignNet : float — 외국인 순매수 (주)
        - institutionNet : float — 기관 순매수 (주)
        - individualNet : float — 개인 순매수 (주)

        KR 외 시장이거나 전체 fallback 실패 시 None.

    Requires:
        네트워크 (KR Naver 직접 호출).

    Raises
    ------
    없음
        fallback 체인 내부 예외는 GatherError/ImportError/OSError 로 흡수.

    Example
    -------
    >>> rows = await fetch("005930", market="KR", limit=20)

    See Also:
        ``dartlab.gather.domains.naver.fetchFlow`` — primary fallback target.
    """
    if market != "KR":
        return None

    for domainName in FLOW_FALLBACK:
        try:
            module = loadDomain(domainName)
            result = await module.fetchFlow(stockCode, client)
            if result:
                if limit is not None and limit > 0:
                    return result[:limit]
                return result
        except (GatherError, ImportError, OSError) as exc:
            log.debug("flow fallback %s 실패: %s", domainName, exc)
            continue
    return None

"""업종 분류 facade -- KR(KIND+Naver)."""

from __future__ import annotations

import logging

from .http import GatherHttpClient
from .types import SectorInfo, SourceUnavailableError

log = logging.getLogger(__name__)


async def fetch(stockCode: str, *, market: str = "KR", client: GatherHttpClient) -> SectorInfo | None:
    """업종 분류 조회 -- KR만 지원.

    Parameters
    ----------
    stockCode : str
        종목코드 (예: "005930").
    market : str
        시장 코드. "KR"만 지원, 그 외 None 반환.
    client : GatherHttpClient
        HTTP 클라이언트.

    Returns
    -------
    SectorInfo | None
        업종 분류 정보. SectorInfo 필드:

        - sectorCode : str — 업종 코드
        - sectorName : str — 업종명
        - industryCode : str — 산업 코드
        - industryName : str — 산업명
        - market : str — 시장 구분 (KOSPI/KOSDAQ)
        - source : str — 데이터 출처

        KR 외 시장이거나 조회 실패 시 None.
    """
    if market != "KR":
        return None
    try:
        from .domains.krx import fetchSectorInfo

        return await fetchSectorInfo(stockCode, client)
    except (SourceUnavailableError, ImportError, OSError) as exc:
        log.warning("sector KR 실패 (%s): %s", stockCode, exc)
        return None

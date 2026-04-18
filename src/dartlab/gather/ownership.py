"""지분 보유 facade -- KR(Naver flow)."""

from __future__ import annotations

import logging

from .http import GatherHttpClient
from .types import InstitutionOwnership, SourceUnavailableError

log = logging.getLogger(__name__)


async def fetch(
    stockCode: str,
    *,
    market: str = "KR",
    client: GatherHttpClient,
) -> list[InstitutionOwnership]:
    """기관/외국인 지분 보유 조회 -- KR만 지원.

    Parameters
    ----------
    stockCode : str
        종목코드 (예: "005930").
    market : str
        시장 코드. "KR"만 지원, 그 외 빈 리스트 반환.
    client : GatherHttpClient
        HTTP 클라이언트.

    Returns
    -------
    list[InstitutionOwnership]
        기관/외국인 지분 리스트. 각 InstitutionOwnership 필드:

        - holderName : str — 보유 주체명 (예: "외국인 합계")
        - ratio : float — 보유비율 (%)
        - source : str — 데이터 출처 ("naver")

        KR 외 시장이거나 조회 실패 시 빈 리스트 [].
    """
    if market != "KR":
        return []
    try:
        url = f"https://m.stock.naver.com/api/stock/{stockCode}/integration"
        resp = await client.get(url)
        data = resp.json()
        dealTrends = data.get("dealTrendInfos", [])
        if not dealTrends:
            return []
        latest = dealTrends[0]
        foreignRatio = _cleanFloat(latest.get("foreignerHoldRatio", "0").replace("%", ""))
        result = []
        if foreignRatio > 0:
            result.append(
                InstitutionOwnership(
                    holderName="외국인 합계",
                    ratio=foreignRatio,
                    source="naver",
                )
            )
        return result
    except (SourceUnavailableError, KeyError, ValueError, TypeError) as exc:
        log.debug("ownership KR 실패 (%s): %s", stockCode, exc)
        return []


def _cleanFloat(text) -> float:
    """숫자 텍스트를 float로 변환. 콤마·공백 제거.

    Parameters
    ----------
    text : str | None
        변환할 텍스트. None이나 빈 문자열이면 0.0 반환.

    Returns
    -------
    float
        변환된 숫자값. 파싱 실패 시 0.0.
    """
    if not text:
        return 0.0
    try:
        return float(str(text).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0.0

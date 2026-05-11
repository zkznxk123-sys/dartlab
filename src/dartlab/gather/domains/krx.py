"""KRX 시장 데이터 수집 -- 업종 분류 + 시총 + 피어 목록.

KRX data.krx.co.kr은 봇 차단이 강력하므로,
KIND 상장목록(listing.py) + Naver 업종 API를 조합하여 수집한다.

소스:
- KIND (kind.krx.co.kr): 업종 분류, 시장구분 -- listing.py 재활용
- Naver (m.stock.naver.com): 업종코드, 업종별 종목 목록(시총 포함)
"""

from __future__ import annotations

import logging

from ..infra.http import GatherHttpClient
from ..types import SectorInfo, SourceUnavailableError

log = logging.getLogger(__name__)

_NAVER_INDUSTRY_LIST = "https://m.stock.naver.com/api/stocks/industry"
_NAVER_INDUSTRY_DETAIL = "https://m.stock.naver.com/api/stocks/industry/{code}"
_NAVER_INTEGRATION = "https://m.stock.naver.com/api/stock/{code}/integration"


async def fetchSectorInfo(stockCode: str, client: GatherHttpClient) -> SectorInfo | None:
    """종목의 업종 분류 조회 -- KIND + Naver 조합.

    Parameters
    ----------
    stockCode : str
        종목코드 (예: ``"005930"``).
    client : GatherHttpClient
        비동기 HTTP 클라이언트.

    Returns
    -------
    SectorInfo | None
        sectorCode : str — 업종코드 (네이버)
        sectorName : str — 업종명 (KIND 우선)
        industryCode : str — 산업코드 (네이버)
        industryName : str — 산업명 (네이버)
        market : str — 시장구분 (코스피/코스닥)
        source : str — ``"kind+naver"``
    """
    # 1) KIND에서 업종명 가져오기 (동기 -- 이미 캐시됨)
    kindSector = _getKindSector(stockCode)

    # 2) Naver에서 업종코드 가져오기
    naverIndustryCode = None
    naverIndustryName = None
    market = ""
    try:
        url = _NAVER_INTEGRATION.format(code=stockCode)
        resp = await client.get(url)
        data = resp.json()
        naverIndustryCode = str(data.get("industryCode", ""))
        exchange = data.get("stockExchangeType", {})
        if isinstance(exchange, dict):
            market = exchange.get("nameKor", "")
        elif isinstance(data.get("sosok"), str):
            market = "코스피" if data["sosok"] == "0" else "코스닥"
    except (SourceUnavailableError, KeyError, ValueError, TypeError) as exc:
        log.debug("Naver integration 실패 (%s): %s", stockCode, exc)

    # 3) 업종코드로 업종명 확인
    if naverIndustryCode:
        naverIndustryName = await _getIndustryName(naverIndustryCode, client)

    sectorName = kindSector or naverIndustryName or ""
    return SectorInfo(
        sectorCode=naverIndustryCode or "",
        sectorName=sectorName,
        industryCode=naverIndustryCode or "",
        industryName=naverIndustryName or "",
        market=market or _getKindMarket(stockCode),
        source="kind+naver",
    )


async def fetchIndustryPeers(industryCode: str, client: GatherHttpClient) -> list[dict]:
    """업종 내 종목 목록 (시총 포함) -- Naver 업종 API.

    Parameters
    ----------
    industryCode : str
        네이버 업종코드 (예: ``"263"``).
    client : GatherHttpClient
        비동기 HTTP 클라이언트.

    Returns
    -------
    list[dict]
        업종 내 종목 목록. 각 dict 키:

        - stockCode : str — 종목코드
        - stockName : str — 종목명
        - closePrice : int — 현재가 (원)
        - marketCap : int — 시가총액 (원)
        - fluctuationsRatio : float — 등락률 (%)
        - market : str — ``"KOSPI"`` | ``"KOSDAQ"``

        조회 실패 시 빈 리스트.
    """
    try:
        url = _NAVER_INDUSTRY_DETAIL.format(code=industryCode)
        resp = await client.get(url)
        data = resp.json()
        stocks = data.get("stocks", [])
        result = []
        for s in stocks:
            code = s.get("itemCode", "")
            if not code:
                continue
            result.append(
                {
                    "stockCode": code,
                    "stockName": s.get("stockName", ""),
                    "closePrice": _cleanNumber(s.get("closePrice", "")),
                    "marketCap": _cleanNumber(s.get("marketValue", "")),
                    "fluctuationsRatio": _cleanFloat(s.get("fluctuationsRatio", "")),
                    "market": "KOSPI" if s.get("sosok") == "0" else "KOSDAQ",
                }
            )
        return result
    except (SourceUnavailableError, KeyError, ValueError, TypeError) as exc:
        log.warning("fetchIndustryPeers 실패 (%s): %s", industryCode, exc)
        return []


async def fetchIndustryList(client: GatherHttpClient) -> list[dict]:
    """전체 업종 목록 조회 -- Naver.

    Parameters
    ----------
    client : GatherHttpClient
        비동기 HTTP 클라이언트.

    Returns
    -------
    list[dict]
        업종 목록. 각 dict 키:

        - industryCode : str — 업종코드
        - industryName : str — 업종명
        - totalCount : int — 소속 종목 수 (개)
        - changeRate : float — 업종 등락률 (%)

        조회 실패 시 빈 리스트.
    """
    try:
        resp = await client.get(_NAVER_INDUSTRY_LIST)
        data = resp.json()
        groups = data.get("groups", [])
        return [
            {
                "industryCode": str(g.get("no", "")),
                "industryName": g.get("name", ""),
                "totalCount": g.get("totalCount", 0),
                "changeRate": _cleanFloat(g.get("changeRate", "")),
            }
            for g in groups
            if g.get("no") and g.get("name")
        ]
    except (SourceUnavailableError, KeyError, ValueError, TypeError) as exc:
        log.warning("fetchIndustryList 실패: %s", exc)
        return []


# ── 내부 헬퍼 ──


def _getKindSector(stockCode: str) -> str:
    """KIND 상장목록에서 업종명을 조회.

    Parameters
    ----------
    stockCode : str
        종목코드 (예: ``"005930"``).

    Returns
    -------
    str
        업종명 (예: ``"전기전자"``). 조회 실패 또는 미등록 시 빈 문자열.
    """
    try:
        import polars as pl

        from dartlab.gather.listing import getKindList

        df = getKindList()
        match = df.filter(pl.col("종목코드") == stockCode)
        if match.height > 0 and "업종" in match.columns:
            return match["업종"][0]
    except (ImportError, FileNotFoundError, ValueError):
        pass
    return ""


def _getKindMarket(stockCode: str) -> str:
    """KIND 상장목록에서 시장구분을 조회.

    Parameters
    ----------
    stockCode : str
        종목코드 (예: ``"005930"``).

    Returns
    -------
    str
        시장명 (``"코스피"`` | ``"코스닥"`` | 원본값). 조회 실패 시 빈 문자열.
    """
    try:
        import polars as pl

        from dartlab.gather.listing import getKindList

        df = getKindList()
        match = df.filter(pl.col("종목코드") == stockCode)
        if match.height > 0 and "시장구분" in match.columns:
            raw = match["시장구분"][0]
            if "유가" in raw:
                return "코스피"
            if "코스닥" in raw:
                return "코스닥"
            return raw
    except (ImportError, FileNotFoundError, ValueError):
        pass
    return ""


_industryNameCache: dict[str, str] = {}


async def _getIndustryName(industryCode: str, client: GatherHttpClient) -> str:
    """업종코드로 업종명을 조회 (모듈 캐시 사용).

    Parameters
    ----------
    industryCode : str
        네이버 업종코드 (예: ``"263"``).
    client : GatherHttpClient
        비동기 HTTP 클라이언트.

    Returns
    -------
    str
        업종명 (예: ``"반도체"``). 매핑 실패 시 빈 문자열.
    """
    if industryCode in _industryNameCache:
        return _industryNameCache[industryCode]
    industries = await fetchIndustryList(client)
    for ind in industries:
        _industryNameCache[ind["industryCode"]] = ind["industryName"]
    return _industryNameCache.get(industryCode, "")


def _cleanNumber(text) -> int:
    """콤마/+기호가 포함된 숫자 텍스트를 int로 변환.

    Parameters
    ----------
    text
        변환할 값. 콤마, +기호는 자동 제거.

    Returns
    -------
    int
        변환된 정수. 빈 값이거나 변환 불가 시 0.
    """
    if not text:
        return 0
    cleaned = str(text).replace(",", "").replace("+", "").strip()
    try:
        return int(cleaned)
    except ValueError:
        return 0


def _cleanFloat(text) -> float:
    """콤마/+기호가 포함된 숫자 텍스트를 float로 변환.

    Parameters
    ----------
    text
        변환할 값. 콤마, +기호는 자동 제거.

    Returns
    -------
    float
        변환된 실수. 빈 값이거나 변환 불가 시 0.0.
    """
    if not text:
        return 0.0
    cleaned = str(text).replace(",", "").replace("+", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0

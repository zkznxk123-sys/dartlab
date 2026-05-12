"""네이버 금융 데이터 수집 — 주가 + 수급 + 업종PER.

네이버 금융 API에서 한국 시장 데이터를 수집한다.
robots.txt 준수, 도메인당 30RPM 이하.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..types import (
    FlowData,
    GatherResult,
    PriceSnapshot,
    RevenueConsensus,
    SourceUnavailableError,
)

log = logging.getLogger(__name__)

# NaverPay 증권 API (JSON)
_API_BASE = "https://m.stock.naver.com/api/stock"
# 네이버 차트 API (XML) — FDR 방식, 한번에 6000일
_CHART_URL = "https://fchart.stock.naver.com/sise.nhn"
# 네이버 분봉 API (JSON) — 당일 1분봉 OHLCV
_INTRADAY_URL = "https://api.stock.naver.com/chart/domestic/item/{code}/minute"


def _cleanNumber(text: str | None) -> float | None:
    """숫자 텍스트 파싱 — 콤마, 공백, +/- 처리.

    Parameters
    ----------
    text : str | None
        파싱할 숫자 문자열. "N/A", "-", 빈 문자열은 None 처리.

    Returns
    -------
    float | None
        파싱된 숫자값. 변환 불가 시 None.
    """
    if not text:
        return None
    cleaned = str(text).strip().replace(",", "").replace("+", "").replace(" ", "")
    if not cleaned or cleaned in ("N/A", "-"):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


# ══════════════════════════════════════
# 개별 데이터 수집 함수
# ══════════════════════════════════════


def _parseInfos(infos: list[dict]) -> dict[str, str]:
    """totalInfos 배열을 {code: value} dict로 변환.

    Parameters
    ----------
    infos : list[dict]
        네이버 integration API의 totalInfos 배열.
        각 항목은 ``{"code": "per", "value": "12.5배"}`` 형태.

    Returns
    -------
    dict[str, str]
        code를 키, value를 값으로 하는 매핑.
        예: ``{"per": "12.5배", "pbr": "1.2배", "marketValue": "100조"}``.
    """
    return {item.get("code", ""): item.get("value", "") for item in infos if item.get("code")}


def _parseMarketCap(text: str) -> float:
    """한글 단위 시가총액 텍스트를 숫자로 변환.

    Parameters
    ----------
    text : str
        네이버 시총 텍스트. 예: ``"1,063조 7,589억"``.

    Returns
    -------
    float
        원 단위 시가총액 (원). 빈 문자열이면 0.0.
    """
    if not text:
        return 0.0
    total = 0.0
    text = text.replace(",", "")
    if "조" in text:
        parts = text.split("조")
        total += (_cleanNumber(parts[0]) or 0.0) * 1_0000_0000_0000
        text = parts[1] if len(parts) > 1 else ""
    if "억" in text:
        parts = text.split("억")
        total += (_cleanNumber(parts[0]) or 0.0) * 1_0000_0000
    return total


def _cleanSuffix(text: str, *suffixes: str) -> str:
    """숫자 텍스트에서 한글 단위 접미사를 제거.

    Parameters
    ----------
    text : str
        단위가 붙은 숫자 문자열. 예: ``"27.38배"``, ``"6,564원"``.
    *suffixes : str
        제거할 접미사 목록. 예: ``"배"``, ``"원"``, ``"%"``.

    Returns
    -------
    str
        접미사 제거 후 strip된 문자열. 예: ``"27.38"``, ``"6,564"``.
    """
    for suffix in suffixes:
        text = text.replace(suffix, "")
    return text.strip()


async def fetchPrice(
    stockCode: str,
    client,
    *,
    limit: int | None = None,
    **kwargs,
) -> PriceSnapshot | None:
    """네이버 -> 현재가 + PER/PBR + 52주 범위 + 시총 (KR 전용).

    Capabilities: KR Naver M-Stock API fetch + PriceSnapshot 변환.
    AIContext: gather.price KR primary source — 가장 풍부한 단건 스냅샷.
    Guide: KR 종목코드 (6자리 숫자) 만. 외 티커는 None.
    When: gather("price", stockCode, market="KR") 진입 시 첫 시도.
    How: m.stock.naver.com integration JSON → PriceSnapshot 매핑.

    KR 종목코드(6자리 숫자)가 아니면 None 반환 — naver KR API에 잘못된
    티커를 보내 409 에러가 나는 것을 차단.

    Parameters
    ----------
    stock_code : str
        종목코드 (예: ``"005930"``). 6자리 숫자만 처리.
    client
        비동기 HTTP 클라이언트.
    limit : int | None
        단건 PriceSnapshot 반환 함수라 무시된다. 인터페이스 호환 목적.

    Returns
    -------
    PriceSnapshot | None
        현재가 스냅샷. KR 종목코드 아니면 None. 주요 필드:

        - current : float — 현재가 (원)
        - change : float — 전일 대비 변동액 (원)
        - change_pct : float — 전일 대비 변동률 (%)
        - high_52w : float — 52주 최고가 (원)
        - low_52w : float — 52주 최저가 (원)
        - volume : int — 누적 거래량 (주)
        - market_cap : float — 시가총액 (원)
        - per : float | None — PER (배)
        - pbr : float | None — PBR (배)
        - dividend_yield : float | None — 배당수익률 (%)
        - source : str — ``"naver"``

        API 실패 또는 현재가 없으면 None.

    Raises
    ------
    없음
        Naver API 내부 예외 (SourceUnavailableError/ValueError 등) 는 흡수.

    Example
    -------
    >>> snap = await fetchPrice("005930", client)
    """
    del limit
    # KR 종목코드 검증 — 6자리 숫자 아니면 차단 (US/글로벌 티커 → naver_global로)
    if not (stockCode and stockCode.strip().isdigit() and len(stockCode.strip()) == 6):
        return None

    # basic: 현재가, 등락
    url = f"{_API_BASE}/{stockCode}/basic"
    try:
        resp = await client.get(url, headers={"Accept": "application/json"})
        data = resp.json()
    except (SourceUnavailableError, ValueError) as exc:
        log.warning("naver price API 실패 (%s): %s", stockCode, exc)
        return None

    current = _cleanNumber(data.get("closePrice"))
    if not current:
        return None

    # integration: 시총, PER, PBR, 52주 범위
    marketCap = 0.0
    per = None
    pbr = None
    high52w = 0.0
    low52w = 0.0
    volume = int(_cleanNumber(data.get("accumulatedTradingVolume")) or 0)
    dividendYield = None

    try:
        intUrl = f"{_API_BASE}/{stockCode}/integration"
        intResp = await client.get(intUrl, headers={"Accept": "application/json"})
        intData = intResp.json()
        infos = _parseInfos(intData.get("totalInfos", []))

        marketCap = _parseMarketCap(infos.get("marketValue", ""))
        per = _cleanNumber(_cleanSuffix(infos.get("per", ""), "배"))
        pbr = _cleanNumber(_cleanSuffix(infos.get("pbr", ""), "배"))
        high52w = _cleanNumber(_cleanSuffix(infos.get("highPriceOf52Weeks", ""), "원")) or 0.0
        low52w = _cleanNumber(_cleanSuffix(infos.get("lowPriceOf52Weeks", ""), "원")) or 0.0
        volume = int(_cleanNumber(infos.get("accumulatedTradingVolume", "").replace("백만", "")) or volume)
        dividendYield = _cleanNumber(_cleanSuffix(infos.get("dividendYieldRatio", ""), "%"))
    except (SourceUnavailableError, ValueError, KeyError):
        log.debug("naver integration fallback 실패 (%s)", stockCode)

    return PriceSnapshot(
        current=current,
        change=_cleanNumber(data.get("compareToPreviousClosePrice")) or 0.0,
        change_pct=_cleanNumber(data.get("fluctuationsRatio")) or 0.0,
        high_52w=high52w,
        low_52w=low52w,
        volume=volume,
        marketCap=marketCap,
        per=per,
        pbr=pbr,
        dividend_yield=dividendYield,
        source="naver",
        fetched_at=datetime.now(timezone.utc).isoformat(),
        currency="KRW",
        market="KR",
    )


async def fetchFlow(
    stockCode: str,
    client,
    *,
    limit: int | None = None,
) -> list[dict] | None:
    """네이버 → 외국인/기관 수급 시계열.

    Capabilities: KR Naver 일별 외국인/기관/개인 순매수 fetch + 표준 dict 변환.
    AIContext: gather.flow KR 의 backend — sources/flow.fetch 호출자.
    Guide: KR 종목만. 외 시장은 빈 list. 최근일 우선 (latest first).
    When: gather("flow", stockCode) 진입 시 fallback chain 첫 시도.
    How: m.stock.naver.com 일별 deal trend JSON → list[dict].

    Parameters
    ----------
    stock_code : str
        종목코드 (예: ``"005930"``).
    client
        비동기 HTTP 클라이언트.
    limit : int | None
        반환 행수 상한 (가장 최근 N건). None이면 전체.

    Returns
    -------
    list[dict] | None
        수급 시계열 (최신순). 각 dict 키:

        - date : str — 거래일 (YYYYMMDD 또는 빈 문자열)
        - foreignNet : float — 외국인 순매수 (주)
        - institutionNet : float — 기관 순매수 (주)
        - individualNet : float — 개인 순매수 (주)
        - foreignHoldingRatio : float — 외국인 보유 비율 (%)

        데이터 없으면 None.

    Raises
    ------
    없음
        Naver API 내부 예외 (SourceUnavailableError/ValueError) 는 흡수.

    Example
    -------
    >>> flow = await fetchFlow("005930", client)
    """
    # KR 종목코드 검증
    if not (stockCode and stockCode.strip().isdigit() and len(stockCode.strip()) == 6):
        return None

    url = f"{_API_BASE}/{stockCode}/integration"
    try:
        resp = await client.get(url, headers={"Accept": "application/json"})
        data = resp.json()
    except (SourceUnavailableError, ValueError) as exc:
        log.warning("naver flow API 실패 (%s): %s", stockCode, exc)
        return None

    # v2: dealTrendInfos 배열 전체 활용 (최신순)
    deal_trends = data.get("dealTrendInfos") or []
    if deal_trends and isinstance(deal_trends, list):
        result = []
        for item in deal_trends:
            fn = _cleanNumber(item.get("foreignerPureBuyQuant"))
            on = _cleanNumber(item.get("organPureBuyQuant"))
            ind = _cleanNumber(item.get("individualPureBuyQuant"))
            ratio_str = item.get("foreignerHoldRatio", "")
            ratio = None
            if ratio_str:
                ratio = _cleanNumber(str(ratio_str).replace("%", ""))
            row = {
                "date": item.get("bizdate", ""),
                "foreignNet": fn or 0.0,
                "institutionNet": on or 0.0,
                "individualNet": ind or 0.0,
                "foreignHoldingRatio": ratio or 0.0,
            }
            result.append(row)
        if result:
            if limit is not None and limit > 0:
                return result[:limit]
            return result

    # v1 fallback: foreignSummary + dealTrendByInvestor (스냅샷 1건)
    foreign_net = 0.0
    institution_net = 0.0
    foreign_holding_ratio = 0.0

    foreign_info = data.get("foreignSummary")
    if foreign_info:
        ratio = _cleanNumber(foreign_info.get("foreignOwnershipRatio"))
        if ratio is not None:
            foreign_holding_ratio = ratio

    investor_info = data.get("dealTrendByInvestor")
    if investor_info and isinstance(investor_info, list):
        for item in investor_info:
            investor_type = item.get("investorType", "")
            net_buy = _cleanNumber(item.get("accumulatedNetBuyVolume"))
            if net_buy is None:
                continue
            if "외국인" in investor_type or investor_type == "FOREIGNER":
                foreign_net = net_buy
            elif "기관" in investor_type or investor_type == "INSTITUTION":
                institution_net = net_buy

    if foreign_net == 0.0 and institution_net == 0.0 and foreign_holding_ratio == 0.0:
        return None

    snapshot = [
        {
            "date": "",
            "foreignNet": foreign_net,
            "institutionNet": institution_net,
            "foreignHoldingRatio": foreign_holding_ratio,
        }
    ]
    if limit is not None and limit > 0:
        return snapshot[:limit]
    return snapshot


async def fetchRevenueConsensus(
    stockCode: str,
    client,
    *,
    limit: int | None = None,
) -> list[RevenueConsensus]:
    """네이버 → 연간 매출/영업이익/순이익 컨센서스.

    Capabilities: KR Naver finance/annual API → 연간 재무 컨센서스 list.
    AIContext: 분석 엔진 (analysis/credit) 의 forward 추정 라인 진입.
    Guide: isConsensus='Y' 기간만. 일반 history 와 분리.
    When: gather.revenueConsensus 류 호출 (사용 빈도 낮음) 시.
    How: finance/annual JSON → list[RevenueConsensus].

    finance/annual API에서 isConsensus='Y'인 기간의 재무 추정치를 추출한다.
    실적 확정 기간(isConsensus='N')도 함께 반환하여 시계열 비교 가능.

    Parameters
    ----------
    stock_code : str
        종목코드 (예: ``"005930"``).
    client
        비동기 HTTP 클라이언트.

    Returns
    -------
    list[RevenueConsensus]
        연간 컨센서스 목록. 각 항목 주요 필드:

        - fiscal_year : int — 사업연도
        - revenue_est : float — 매출액 추정치 (억원)
        - operating_profit_est : float | None — 영업이익 추정치 (억원)
        - net_income_est : float | None — 당기순이익 추정치 (억원)
        - eps_est : float | None — EPS 추정치 (원)
        - per_est : float | None — PER 추정치 (배)
        - source : str — ``"naver_consensus"`` 또는 ``"naver_actual"``

        API 실패 또는 데이터 없으면 빈 리스트.

    Other Parameters
    ----------------
    limit : int | None
        반환 행수 상한. None이면 전체.

    Raises
    ------
    없음
        Naver finance/annual API 내부 예외 (SourceUnavailableError/ValueError) 는 흡수.

    Example
    -------
    >>> rows = await fetchRevenueConsensus("005930", client)
    """
    # KR 종목코드 검증
    if not (stockCode and stockCode.strip().isdigit() and len(stockCode.strip()) == 6):
        return []

    url = f"{_API_BASE}/{stockCode}/finance/annual"
    try:
        resp = await client.get(url, headers={"Accept": "application/json"})
        data = resp.json()
    except (SourceUnavailableError, ValueError) as exc:
        log.warning("naver finance/annual API 실패 (%s): %s", stockCode, exc)
        return []

    fi = data.get("financeInfo")
    if not fi:
        return []

    titles = fi.get("trTitleList", [])
    rows = fi.get("rowList", [])
    if not titles or not rows:
        return []

    # 항목별 dict 구축
    row_map: dict[str, dict] = {}
    for row in rows:
        title = row.get("title", "")
        cols = row.get("columns")
        if title and isinstance(cols, dict):
            row_map[title] = cols

    results: list[RevenueConsensus] = []
    for t in titles:
        key = t.get("key", "")
        is_consensus = t.get("isConsensus") == "Y"
        if not key or len(key) < 4:
            continue

        fiscal_year = int(key[:4])

        revenue = _cleanNumber(row_map.get("매출액", {}).get(key, {}).get("value"))
        op_profit = _cleanNumber(row_map.get("영업이익", {}).get(key, {}).get("value"))
        net_income = _cleanNumber(row_map.get("당기순이익", {}).get(key, {}).get("value"))
        eps = _cleanNumber(row_map.get("EPS", {}).get(key, {}).get("value"))
        per = _cleanNumber(row_map.get("PER", {}).get(key, {}).get("value"))

        if revenue is None and op_profit is None:
            continue

        results.append(
            RevenueConsensus(
                fiscal_year=fiscal_year,
                revenue_est=revenue or 0.0,
                operating_profit_est=op_profit,
                net_income_est=net_income,
                eps_est=eps,
                per_est=per,
                source="naver_consensus" if is_consensus else "naver_actual",
            )
        )

    if limit is not None and limit > 0:
        return results[:limit]
    return results


async def fetchSectorPer(
    stockCode: str,
    client,
    *,
    limit: int | None = None,
) -> float | None:
    """네이버 → 동종업종 PER.

    Capabilities: KR Naver finance/sector API → 동종업종 평균 PER 단건 float.
    AIContext: peer-relative valuation 분석 baseline — relativeValuation 진입.
    Guide: 단건 float 반환 — limit 무시.
    When: 종목의 동종업종 평균 PER 비교 시.
    How: finance/sector JSON parse → sector PER float.

    Parameters
    ----------
    stock_code : str
        종목코드 (예: ``"005930"``).
    client
        비동기 HTTP 클라이언트.
    limit : int | None
        단건 float 반환 함수라 무시된다. 인터페이스 호환 목적.

    Returns
    -------
    float | None
        동종업종 평균 PER (배). API 실패 또는 데이터 없으면 None.

    Raises
    ------
    없음
        Naver integration API 내부 예외 (SourceUnavailableError/ValueError) 는 흡수.

    Example
    -------
    >>> per = await fetchSectorPer("005930", client)
    """
    del limit
    # KR 종목코드 검증
    if not (stockCode and stockCode.strip().isdigit() and len(stockCode.strip()) == 6):
        return None

    url = f"{_API_BASE}/{stockCode}/integration"
    try:
        resp = await client.get(url, headers={"Accept": "application/json"})
        data = resp.json()
    except (SourceUnavailableError, ValueError) as exc:
        log.warning("naver sector PER API 실패 (%s): %s", stockCode, exc)
        return None

    industry_info = data.get("industryInfo")
    if not industry_info:
        return None

    return _cleanNumber(industry_info.get("per"))


# ══════════════════════════════════════
# 통합 수집
# ══════════════════════════════════════


async def fetchAll(
    stockCode: str,
    client,
    *,
    limit: int | None = None,
) -> GatherResult:
    """네이버에서 가져올 수 있는 모든 데이터를 수집.

    Capabilities: 한 종목코드 fetch 1 회로 GatherResult (price + flow + ...) 일괄.
    AIContext: collect mixin 의 KR 도메인 fan-out 진입.
    Guide: 부분 결과 가능 — 일부 axis 실패는 다른 axis 결과로 진행.
    When: gather.collect mixin 호출 시 KR 도메인 진입.
    How: fetchPrice/fetchFlow 등 병렬 호출 → GatherResult 통합.

    Parameters
    ----------
    stock_code : str
        종목코드 (예: ``"005930"``).
    client
        비동기 HTTP 클라이언트.
    limit : int | None
        단건 GatherResult 반환 함수라 무시된다. 인터페이스 호환 목적.

    Returns
    -------
    GatherResult
        domain : str — ``"naver"``
        price : PriceSnapshot | None — 현재가 스냅샷
        flow : FlowData | None — 외국인/기관 수급 스냅샷
        sector_per : float | None — 동종업종 PER (배)
        error : str | None — 수집 실패 시 에러 메시지

    Raises
    ------
    없음
        SourceUnavailableError 는 GatherResult.error 로 흡수.

    Example
    -------
    >>> r = await fetchAll("005930", client)
    """
    del limit
    result = GatherResult(domain="naver")
    try:
        result.price = await fetchPrice(stockCode, client)
        # flow: 시계열 → 스냅샷 변환 (GatherResult 호환)
        flow_series = await fetchFlow(stockCode, client)
        if flow_series:
            latest = flow_series[0]
            result.flow = FlowData(
                foreign_net=latest.get("foreignNet") or 0.0,
                institution_net=latest.get("institutionNet") or 0.0,
                foreign_holding_ratio=latest.get("foreignHoldingRatio") or 0.0,
                source="naver",
            )
        result.sector_per = await fetchSectorPer(stockCode, client)
    except SourceUnavailableError as exc:
        result.error = str(exc)
    return result


async def fetchIntraday(
    stockCode: str,
    client,
    *,
    market: str = "KR",
    limit: int | None = None,
    **_: object,
) -> list[dict]:
    """네이버 → 당일 1분봉 OHLCV.

    Capabilities: KR Naver api.stock.naver.com 1분봉 list[dict].
    AIContext: intraday 분석 (gap/spike 분 단위) 의 raw 원천.
    Guide: 당일 한정. 과거일 1분봉은 별도 source (daily 만).
    When: intraday 가격 변동 분석 시.
    How: api.stock.naver.com intraday JSON → list[dict].

    api.stock.naver.com 엔드포인트. minuteType/count 파라미터는 서버가 무시하므로
    당일분 전체가 한 번에 온다. 5/15/30/60분봉은 이 결과를 Polars로 리샘플하여 얻는다.
    과거 분봉은 제공하지 않음 (fchart는 OHL=null이라 미사용).

    Parameters
    ----------
    stock_code : str
        종목코드 (예: ``"005930"``).
    client
        비동기 HTTP 클라이언트.
    market : str
        시장 코드. ``"KR"`` 외에는 빈 리스트 반환.
    limit : int | None
        반환 행수 상한 (가장 최근 N분). None이면 당일 전체.

    Returns
    -------
    list[dict]
        당일 1분봉 OHLCV 목록. 각 dict 키:

        - datetime : str — ISO8601 (``YYYY-MM-DDTHH:MM:SS``, KST)
        - open : float — 시가 (원)
        - high : float — 고가 (원)
        - low : float — 저가 (원)
        - close : float — 종가 (원)
        - volume : int — 누적 거래량 (주)

        KR 외 시장이거나 조회 실패 시 빈 리스트.

    Raises
    ------
    없음
        Naver intraday API 내부 예외 (SourceUnavailableError/ValueError) 는 흡수.

    Example
    -------
    >>> rows = await fetchIntraday("005930", client, market="KR")
    """
    if market != "KR":
        return []
    # KR 종목코드 검증
    if not (stockCode and stockCode.strip().isdigit() and len(stockCode.strip()) == 6):
        return []

    url = _INTRADAY_URL.format(code=stockCode)
    try:
        resp = await client.get(url, headers={"Accept": "application/json"})
        data = resp.json()
    except (SourceUnavailableError, ValueError) as exc:
        log.warning("naver intraday API 실패 (%s): %s", stockCode, exc)
        return []

    if not isinstance(data, list):
        return []

    rows: list[dict] = []
    for item in data:
        dt = item.get("localDateTime", "")
        if len(dt) < 14:
            continue
        close = item.get("currentPrice")
        if close is None:
            continue
        rows.append(
            {
                "datetime": f"{dt[:4]}-{dt[4:6]}-{dt[6:8]}T{dt[8:10]}:{dt[10:12]}:{dt[12:14]}",
                "open": float(item.get("openPrice") or 0.0),
                "high": float(item.get("highPrice") or 0.0),
                "low": float(item.get("lowPrice") or 0.0),
                "close": float(close),
                "volume": int(item.get("accumulatedTradingVolume") or 0),
            }
        )
    if limit is not None and limit > 0:
        return rows[-limit:]
    return rows


async def fetchHistory(
    stockCode: str,
    client,
    *,
    start: str = "",
    end: str = "",
    market: str = "KR",
    limit: int | None = None,
) -> list[dict]:
    """네이버 차트 API — 한번에 6000일 수정주가 OHLCV (FDR 방식).

    Capabilities: KR Naver fchart 6000일 수정주가 일별 OHLCV bulk fetch.
    AIContext: gather.history KR primary backend — backtest/timeseries 진입.
    Guide: 단일 호출로 6000일 수정주가. fchart 의 adjustment 표준.
    When: KR 종목의 장기 일별 OHLCV 필요 시 (백테스트, 추세 분석).
    How: fchart.stock.naver.com sise.nhn → text parse → list[dict].

    Parameters
    ----------
    stock_code : str
        종목코드 (예: ``"005930"``).
    client
        비동기 HTTP 클라이언트.
    start : str
        시작일 (YYYY-MM-DD). 빈 문자열이면 필터 없음.
    end : str
        종료일 (YYYY-MM-DD). 빈 문자열이면 필터 없음.
    market : str
        시장 코드. ``"KR"`` 외에는 빈 리스트 반환.
    limit : int | None
        반환 행수 상한 (가장 최근 N일). None이면 [start, end] 전체.

    Returns
    -------
    list[dict]
        수정주가 OHLCV 행 목록 (날짜 오름차순). 각 dict 키:

        - date : str — 거래일 (YYYY-MM-DD)
        - open : float — 시가 (원)
        - high : float — 고가 (원)
        - low : float — 저가 (원)
        - close : float — 종가 (원)
        - volume : int — 거래량 (주)

        KR 외 시장이거나 조회 실패 시 빈 리스트.

    Raises
    ------
    없음
        Naver chart API 내부 예외 (SourceUnavailableError/OSError) 는 흡수.

    Example
    -------
    >>> rows = await fetchHistory("005930", client, start="2024-01-01")
    """
    if market != "KR":
        return []
    # KR 종목코드 검증 (지수 심볼 KOSPI/KOSDAQ 등도 허용)
    sc = stockCode.strip() if stockCode else ""
    if not (sc.isdigit() and len(sc) == 6) and sc not in ("KOSPI", "KOSDAQ", "KPI200"):
        return []
    import re

    try:
        resp = await client.get(
            _CHART_URL,
            params={
                "timeframe": "day",
                "count": "6000",
                "requestType": "0",
                "symbol": stockCode,
            },
        )
        text = resp.text
    except (SourceUnavailableError, OSError) as exc:
        log.debug("naver chart API 실패: %s", exc)
        return []

    items = re.findall(r'<item data="(.*?)" />', text)
    if not items:
        return []

    rows: list[dict] = []
    for item in items:
        parts = item.split("|")
        if len(parts) < 6:
            continue
        d = parts[0]
        dt = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
        if start and dt < start:
            continue
        if end and dt > end:
            continue
        o = float(parts[1]) if parts[1] else 0.0
        # 거래정지일 (open=0) 건너뛰기
        if o == 0.0:
            continue
        rows.append(
            {
                "date": dt,
                "open": o,
                "high": float(parts[2]) if parts[2] else 0.0,
                "low": float(parts[3]) if parts[3] else 0.0,
                "close": float(parts[4]) if parts[4] else 0.0,
                "volume": int(parts[5]) if parts[5] else 0,
            }
        )
    if limit is not None and limit > 0:
        return rows[-limit:]  # 날짜 오름차순 (수정주가)
    return rows  # 날짜 오름차순 (수정주가)

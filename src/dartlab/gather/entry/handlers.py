"""gather entry — 12 axis dispatch handler 함수 (G+ P-Q2.1).

GatherEntry._run 의 if-elif chain 을 free function 으로 분리. main.py 의
``_AXIS_DISPATCH`` table 이 axis → handler 매핑 → 새 axis 추가 시 두 군데
(``dispatch.AXIS_REGISTRY`` + 본 모듈) 추가하면 dispatch 자동.

handler 시그니처 통일: ``(g, target, *, market, start, end, marketExplicit, **kwargs) -> pl.DataFrame``.
각 handler 가 자신에게 필요 없는 인자는 무시.

Capabilities:
    - 12 axis (price/flow/macro/news/sector/insider/ownership/peers/krx/krxIndex/calendar/dartDoc)
    - 시장 지수 (KOSPI/KOSDAQ/KPI200) 자동 인식 (price)
    - macro 의 _marketExplicit 분기 보존 (target/market 위치 모호성 해소)
    - krx 의 legacyDate alias / krxIndex 의 indexMarket 분리

AIContext:
    - 새 axis 추가 시 본 모듈 + dispatch.AXIS_REGISTRY 두 곳만 갱신.
    - _run if-chain 분석 필요 없음 — handler 본문이 자기 axis 전체 책임.

Guide:
    Engine 본체 (gather.Gather) 가 ``getDefaultGather()`` 를 통해 주입된다.
    handler 는 인스턴스 메서드 호출 (g.price(...) 등) 위주, axis 별 후처리
    (DataFrame reshape, indicator 추가) 도 포함.

When:
    GatherEntry._run 이 _AXIS_DISPATCH[axis] lookup → handler 호출 시.

How:
    handler 추가 절차:
        1. ``def handle<Axis>(g, target, *, market, ...) -> pl.DataFrame`` 작성
        2. ``main.py`` 의 ``_AXIS_DISPATCH`` 에 ``{"axis": handle<Axis>}`` 추가
        3. ``dispatch.py`` 의 ``AXIS_REGISTRY`` 에 메타 추가

Requires:
    ``dartlab.gather.Gather`` 인스턴스 (g). 각 handler 가 자체 import
    (krx/krxIndex 의 gatherKrx/gatherKrxIndex, dartDoc 의 viewer.fetch).

Raises:
    ValueError — 빈 결과 / target 누락 / 폐기 axis (calendar) / 미지원 axis.

Example::

    from dartlab.gather import getDefaultGather
    from dartlab.gather.entry.handlers import handlePrice
    g = getDefaultGather()
    df = handlePrice(g, "005930", market="KR", start=None, end=None, marketExplicit=False)

See Also:
    ``dartlab.gather.entry.main.GatherEntry._run`` — handler 호출 진입점.
    ``dartlab.gather.entry.dispatch.AXIS_REGISTRY`` — axis 메타데이터.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import polars as pl

from .dispatch import INDEX_SYMBOLS, _fetchNaverIndex

log = logging.getLogger(__name__)

# Sprint 3 PR3 — 글로벌 자산 ID 정규식
_ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
_FIGI_RE = re.compile(r"^BBG[A-Z0-9]{9}$")

# OpenFIGI exchCode → marketConfig market 코드 매핑 (주요만).
# 미등록은 사용자 지정 market 유지.
_OPENFIGI_EXCH_TO_MARKET: dict[str, str] = {
    "US": "US",
    "UN": "US",  # NYSE/Nasdaq Composite
    "UQ": "US",  # Nasdaq Global Market
    "UR": "US",  # NYSE Arca
    "KS": "KR",
    "KQ": "KR",
    "JT": "JP",
    "HK": "HK",
    "LN": "UK",
    "GR": "DE",
    "CH": "CN",
    "SZ": "CN",
    "IN": "IN",
    "CT": "CA",
    "AT": "AU",
    "BZ": "BR",
    "SJ": "ZA",
    "MM": "MX",
    "SP": "SG",
    "TB": "TH",
}


def _maybeResolveAssetId(
    target: str | None,
    market: str,
    marketExplicit: bool,
) -> tuple[str | None, str]:
    """target 이 ISIN/FIGI 형식이면 symbology 위임 → (ticker, market) 변환.

    Sig: ``_maybeResolveAssetId(target, market, marketExplicit) -> (target, market)``

    Capabilities: ISIN/FIGI 정규식 매치 → symbology 헬퍼 호출 → ticker 추출.
    AIContext: handlePrice 진입 직후 hook — TICKER 이면 no-op.
    Guide: marketExplicit=True 면 사용자 명시 market 우선. False 면 OpenFIGI exch → market.
    When: handlePrice 진입.
    How: 정규식 매치 → isinToTicker/figiToTicker → exch 매핑 (옵션) → 변환된 target 반환.

    Args:
        target: 사용자 입력 (ticker / ISIN / FIGI).
        market: 사용자 명시 market.
        marketExplicit: True 면 market 변경 금지.

    Returns:
        ``(target, market)`` — ISIN/FIGI 변환 성공 시 ticker + (옵션) 매핑 market.
        실패/TICKER 입력 시 (원본, 원본).

    Raises:
        없음 — 모든 예외 흡수.

    Example:
        >>> _maybeResolveAssetId("US0378331005", "KR", False)
        ('AAPL', 'US')

    See Also:
        ``dartlab.gather.mapping.symbology`` — 위임 대상.
    """
    if not target:
        return target, market
    try:
        # FIGI 우선 (BBG prefix 명확). FIGI 도 ISIN 정규식에 우연히 매치할 수 있으므로 먼저.
        if _FIGI_RE.match(target):
            from dartlab.gather.mapping.symbology import figiToTicker

            resolved = figiToTicker(target)
            if resolved is None:
                return target, market
            new_ticker, exch = resolved
            new_market = market if marketExplicit else _OPENFIGI_EXCH_TO_MARKET.get(exch, market)
            log.info("symbology FIGI→ticker: %s → %s (market=%s)", target, new_ticker, new_market)
            return new_ticker, new_market
        if _ISIN_RE.match(target):
            from dartlab.gather.mapping.symbology import isinToTicker

            resolved = isinToTicker(target)
            if resolved is None:
                return target, market
            new_ticker, exch = resolved
            new_market = market if marketExplicit else _OPENFIGI_EXCH_TO_MARKET.get(exch, market)
            log.info("symbology ISIN→ticker: %s → %s (market=%s)", target, new_ticker, new_market)
            return new_ticker, new_market
    except Exception as exc:  # noqa: BLE001 — silent observer (handler 흐름 차단 금지)
        log.debug("symbology lookup 실패 (target=%s, silent): %s", target, exc)
    return target, market


def handlePrice(
    g: Any,
    target: str | None,
    *,
    market: str,
    start: str | None,
    end: str | None,
    marketExplicit: bool,  # noqa: ARG001 — uniform signature
    **kwargs: Any,
) -> pl.DataFrame:
    """price axis dispatch — OHLCV 시계열 + 보조지표 옵션.

    Capabilities: target → 종목/지수 자동 인식 → g.price 또는 _fetchNaverIndex.
    AIContext: gather("price", ...) 의 본체 — handler dispatch 진입 첫 axis.
    Guide: target 이 INDEX_SYMBOLS 매핑되면 시장 지수, 아니면 종목.
    When: GatherEntry._run("price", target, ...) lookup 시.
    How: target 분기 → g.price() 또는 _fetchNaverIndex() → DataFrame.

    Args:
        g: Gather 싱글턴 인스턴스.
        target: 종목코드/티커 또는 시장 지수 심볼.
        market: "KR" | "US".
        start: 시작일 (YYYY-MM-DD) 또는 None.
        end: 종료일 (YYYY-MM-DD) 또는 None.
        marketExplicit: 무시 (price 는 market 인자 모호성 없음).
        **kwargs: indicators (basic|True|False|list[str]).

    Returns:
        pl.DataFrame — OHLCV + 보조지표 컬럼.

    Raises:
        ValueError — 결과가 빈 DataFrame 일 때.

    Example::

        df = handlePrice(g, "005930", market="KR", start=None, end=None, marketExplicit=False)

    Requires:
        Gather 인스턴스 (g) + dispatch.INDEX_SYMBOLS 매핑 + 시장별 price source 가용.

    See Also:
        main.GatherEntry._run : 본 handler 의 dispatch caller.
        dispatch.AXIS_REGISTRY : axis 메타.
        transforms/indicatorDispatch.addIndicators : 보조지표 후처리.
    """
    # Sprint 3 PR3 — ISIN/FIGI 자동 감지 → symbology 위임 → ticker 변환
    target, market = _maybeResolveAssetId(target, market, marketExplicit)

    if target and target in INDEX_SYMBOLS:
        result = _fetchNaverIndex(INDEX_SYMBOLS[target])
    else:
        result = g.price(target, market=market, start=start, end=end)
    if result is None or (hasattr(result, "shape") and result.shape == (0, 0)):
        raise ValueError(
            f"gather('price', '{target}') 결과가 비어 있습니다. "
            f"종목코드/티커를 확인하세요 (market={market}). "
            f"네트워크 또는 외부 API 일시적 오류일 수도 있습니다."
        )
    indicators = kwargs.pop("indicators", "basic")
    if indicators == "basic":
        indicators = ["sma5", "sma20", "sma60", "ema12", "ema26", "rsi14", "macd", "atr14", "obv"]
    elif indicators is False:
        indicators = None
    if indicators:
        from dartlab.gather.transforms.indicatorDispatch import addIndicators

        result = addIndicators(result, indicators=indicators)
    return result


def handleFlow(
    g: Any,
    target: str | None,
    *,
    market: str,
    start: str | None,  # noqa: ARG001
    end: str | None,  # noqa: ARG001
    marketExplicit: bool,  # noqa: ARG001
    **kwargs: Any,  # noqa: ARG001
) -> pl.DataFrame:
    """flow axis dispatch — 외국인/기관 수급.

    Capabilities: target → g.flow → 일별 외국인/기관/개인 순매수 DataFrame.
    AIContext: gather("flow", ...) 본체 — flow mixin 위임 + reshape.
    Guide: KR 만. 외 시장 target 은 None / 빈 결과.
    When: GatherEntry._run("flow", target, ...) lookup 시.
    How: g.flow(target, market="KR") → list[dict] → pl.DataFrame.

    Args:
        g: Gather 싱글턴.
        target: 종목코드/티커.
        market: "KR" 만 지원 (Naver 한정).
        start/end/marketExplicit/**kwargs: 무시.

    Returns:
        pl.DataFrame — 외국인/기관 순매수 시계열.

    Raises:
        없음 — 빈 결과는 빈 DataFrame.

    Example::

        df = handleFlow(g, "005930", market="KR", start=None, end=None, marketExplicit=False)

    Requires:
        Gather 인스턴스 + KR 시장 (Naver flow API). 외 시장 빈 결과.

    See Also:
        main.GatherEntry._run : dispatch caller.
        mixins/info.flow : 본 handler 가 호출하는 backend.
    """
    return g.flow(target, market=market)


def handleMacro(
    g: Any,
    target: str | None,
    *,
    market: str,
    start: str | None,
    end: str | None,
    marketExplicit: bool,
    **kwargs: Any,
) -> pl.DataFrame:
    """macro axis dispatch — ECOS/FRED 거시지표.

    Capabilities: target → market 자동 감지 → g.macro 위임.
    AIContext: gather("macro", ...) 본체 — ECOS/FRED 라우팅 진입.
    Guide: marketExplicit=False 시 target → _detectMarket 으로 KR/US 자동.
    When: GatherEntry._run("macro", indicator|market, ...) lookup 시.
    How: marketExplicit 분기 → g.macro(market, indicator) 또는 (indicator).

    Args:
        g: Gather 싱글턴.
        target: 지표 코드 (예: "FEDFUNDS", "BASE_RATE") 또는 None (전체).
        market: "KR" (ECOS) | "US" (FRED).
        start/end: ISO date 또는 None.
        marketExplicit: True 면 (market, target) 명시 호출 → `g.macro(market, target, ...)`.
            False 면 target 만 의미 → `g.macro(target, ...)`.
        **kwargs: apiKey, scope.

    Returns:
        pl.DataFrame — 거시지표 시계열.

    Raises:
        없음 — 외부 API 실패 시 빈 DataFrame.

    Example::

        df = handleMacro(g, "CPI", market="KR", start=None, end=None, marketExplicit=False)

    Requires:
        Gather 인스턴스 + market 분기에 따라 ECOS/FRED API 키 (env). marketExplicit 분기.

    See Also:
        main.GatherEntry._run : dispatch caller.
        mixins/macro : 본 handler 가 호출하는 backend.
        macroProvider : MacroProvider Protocol 위임 진입점.
    """
    apiKey = kwargs.pop("apiKey", None)
    scope = kwargs.pop("scope", "default")
    if target is None:
        return g.macro(market, start=start, end=end, apiKey=apiKey, scope=scope)
    if marketExplicit:
        return g.macro(market, target, start=start, end=end, apiKey=apiKey, scope=scope)
    return g.macro(target, start=start, end=end, apiKey=apiKey, scope=scope)


def handleNews(
    g: Any,
    target: str | None,
    *,
    market: str,
    start: str | None,  # noqa: ARG001
    end: str | None,  # noqa: ARG001
    marketExplicit: bool,  # noqa: ARG001
    **kwargs: Any,
) -> pl.DataFrame:
    """news axis dispatch — Google News RSS.

    Capabilities: target query → g.news → 뉴스 DataFrame (title/link/published).
    AIContext: gather("news", ...) 본체 — RSS 결과 untrusted external 마커.
    Guide: market KR/US 검색 지역. days kwarg 로 기간 조정.
    When: GatherEntry._run("news", query, ...) lookup 시.
    How: g.news(query, market=market, days=days) → pl.DataFrame.

    Args:
        g: Gather 싱글턴.
        target: 검색어 (기업명/키워드).
        market: "KR" | "US" (검색 지역).
        start/end/marketExplicit: 무시.
        **kwargs: days (default 30).

    Returns:
        pl.DataFrame — (title, link, pubDate) 행.

    Raises:
        없음 — 외부 RSS 실패 시 빈 DataFrame.

    Example::

        df = handleNews(g, "삼성전자", market="KR", start=None, end=None, marketExplicit=False, days=7)

    Requires:
        Gather 인스턴스 + 네트워크 (Google News RSS). 결과 본문은 untrusted external.

    See Also:
        main.GatherEntry._run : dispatch caller.
        mixins/news.news : 본 handler 가 호출하는 backend.
        formatting.wrap_external_in_result : 본문 untrusted 마커 wrap.
    """
    days = kwargs.pop("days", 30)
    return g.news(target, market=market, days=days)


def handleSector(
    g: Any,
    target: str | None,
    *,
    market: str,
    start: str | None,  # noqa: ARG001
    end: str | None,  # noqa: ARG001
    marketExplicit: bool,  # noqa: ARG001
    **kwargs: Any,  # noqa: ARG001
) -> pl.DataFrame:
    """sector axis dispatch — 업종 분류 (SectorInfo → DataFrame).

    Capabilities: target → g.sector → SectorInfo → 1-row DataFrame.
    AIContext: gather("sector", ...) 본체 — peer matching / industry 분석 진입.
    Guide: 단일 SectorInfo 라 DataFrame 1행. None 이면 ValueError.
    When: GatherEntry._run("sector", stockCode, ...) lookup 시.
    How: g.sector(target, market=market) → SectorInfo → DataFrame.

    Args:
        g: Gather 싱글턴.
        target: 종목코드.
        market: "KR" | "US".
        start/end/marketExplicit/**kwargs: 무시.

    Returns:
        pl.DataFrame (1 행) — sectorCode/sectorName/industryCode/industryName/market.

    Raises:
        없음 — sector 미확인 시 빈 DataFrame.

    Example::

        df = handleSector(g, "005930", market="KR", start=None, end=None, marketExplicit=False)

    Requires:
        Gather 인스턴스 + KR 시장 (KIND+Naver). g.sector 가 SectorInfo 반환.

    See Also:
        main.GatherEntry._run : dispatch caller.
        mixins/info.sector : 본 handler 가 호출하는 backend.
        domains/krx.fetchSectorInfo : 실제 KIND+Naver fetch.
    """
    result = g.sector(target, market=market)
    if result is None:
        return pl.DataFrame()
    return pl.DataFrame(
        [
            {
                "sectorCode": result.sectorCode,
                "sectorName": result.sectorName,
                "industryCode": result.industryCode,
                "industryName": result.industryName,
                "market": result.market,
            }
        ]
    )


def handleInsider(
    g: Any,
    target: str | None,
    *,
    market: str,
    start: str | None,  # noqa: ARG001
    end: str | None,  # noqa: ARG001
    marketExplicit: bool,  # noqa: ARG001
    **kwargs: Any,  # noqa: ARG001
) -> pl.DataFrame:
    """insider axis dispatch — 내부자 거래 (list → DataFrame).

    Capabilities: target → g.insiderTrading → InsiderTrade list → DataFrame.
    AIContext: gather("insider", ...) 본체 — informed trading 분석 진입.
    Guide: KR 의 경우 DART_API_KEY 필요.
    When: GatherEntry._run("insider", stockCode, ...) lookup 시.
    How: g.insiderTrading(target, market) → list[InsiderTrade] → DataFrame.

    Args:
        g: Gather 싱글턴.
        target: 종목코드.
        market: "KR" — DART 의 내부자 공시 (DART_API_KEY 필요).
        start/end/marketExplicit/**kwargs: 무시.

    Returns:
        pl.DataFrame — 거래일/거래자/직위/거래유형/변동주수.

    Raises:
        없음 — API 실패 또는 거래 없음 시 빈 DataFrame.

    Example::

        df = handleInsider(g, "005930", market="KR", start=None, end=None, marketExplicit=False)

    Requires:
        Gather 인스턴스 + KR 의 경우 ``DART_API_KEY`` env 필요.

    See Also:
        main.GatherEntry._run : dispatch caller.
        mixins/info.insiderTrading : 본 handler 가 호출하는 backend.
        accessors.fetchInsiderTrades / iterInsiderTrades : 신규 streaming 동행.
    """
    trades = g.insiderTrading(target, market=market)
    if not trades:
        return pl.DataFrame()
    return pl.DataFrame(
        [
            {
                "date": t.date,
                "name": t.name,
                "position": t.position,
                "tradeType": t.tradeType,
                "changeShares": t.changeShares,
            }
            for t in trades
        ]
    )


def handleOwnership(
    g: Any,
    target: str | None,
    *,
    market: str,
    start: str | None,  # noqa: ARG001
    end: str | None,  # noqa: ARG001
    marketExplicit: bool,  # noqa: ARG001
    **kwargs: Any,  # noqa: ARG001
) -> pl.DataFrame:
    """ownership axis dispatch — 기관/외국인 지분 (list → DataFrame).

    Capabilities: target → g.ownership → InstitutionOwnership list → DataFrame.
    AIContext: gather("ownership", ...) 본체 — 기관/외국인 보유 분포 진입.
    Guide: KR/US 모두 지원. 빈 list 면 빈 DataFrame.
    When: GatherEntry._run("ownership", stockCode, ...) lookup 시.
    How: g.ownership(target, market) → list[InstitutionOwnership] → DataFrame.

    Args:
        g: Gather 싱글턴.
        target: 종목코드.
        market: "KR" (Naver) | "US".
        start/end/marketExplicit/**kwargs: 무시.

    Returns:
        pl.DataFrame — holderName/ratio/shares/value.

    Raises:
        없음 — fetch 실패 시 빈 DataFrame.

    Example::

        df = handleOwnership(g, "005930", market="KR", start=None, end=None, marketExplicit=False)

    Requires:
        Gather 인스턴스 + 시장별 ownership source (KR: Naver, US: SEC 13F).

    See Also:
        main.GatherEntry._run : dispatch caller.
        mixins/info.ownership : 본 handler 가 호출하는 backend.
        accessors.fetchOwnership / iterOwnership : 신규 streaming 동행.
    """
    owners = g.ownership(target, market=market)
    if not owners:
        return pl.DataFrame()
    return pl.DataFrame(
        [
            {
                "holderName": o.holderName,
                "ratio": o.ratio,
                "shares": o.shares,
                "value": o.value,
            }
            for o in owners
        ]
    )


def handlePeers(
    g: Any,
    target: str | None,
    *,
    market: str,
    start: str | None,  # noqa: ARG001
    end: str | None,  # noqa: ARG001
    marketExplicit: bool,  # noqa: ARG001
    **kwargs: Any,  # noqa: ARG001
) -> pl.DataFrame:
    """peers axis dispatch — 동종업종 피어 종목.

    Capabilities: target → g.industryPeers → 같은 업종 종목 + 시총 DataFrame.
    AIContext: gather("peers", ...) 본체 — peer-relative 비교 진입.
    Guide: KR 만 (KRX 카테고리). sector() 가 먼저 정상 결과 필요.
    When: GatherEntry._run("peers", stockCode, ...) lookup 시.
    How: g.industryPeers(target) → list[dict] → DataFrame.

    Args:
        g: Gather 싱글턴.
        target: 종목코드.
        market: "KR" (KRX/Naver).
        start/end/marketExplicit/**kwargs: 무시.

    Returns:
        pl.DataFrame — 피어 종목 (종목코드+시총).

    Raises:
        없음 — peer 미발견 시 빈 DataFrame.

    Example::

        df = handlePeers(g, "005930", market="KR", start=None, end=None, marketExplicit=False)

    Requires:
        Gather 인스턴스 + KR 시장 + 종목의 industryCode 가 sector 결과로 식별 가능.

    See Also:
        main.GatherEntry._run : dispatch caller.
        mixins/info.industryPeers : 본 handler 가 호출하는 backend.
        domains/krx.fetchIndustryPeers : 실제 Naver peer fetch.
    """
    peers = g.industryPeers(target, market=market)
    if not peers:
        return pl.DataFrame()
    return pl.DataFrame(peers)


def handleKrx(
    g: Any,  # noqa: ARG001 — gatherKrx 직접 호출
    target: str | None,
    *,
    market: str,
    start: str | None,
    end: str | None,
    marketExplicit: bool,  # noqa: ARG001
    **kwargs: Any,
) -> pl.DataFrame:
    """krx axis dispatch — KOSPI/KOSDAQ 전종목 wide pivot.

    Capabilities: target/start/end → gatherKrx → 전종목 wide DataFrame.
    AIContext: gather("krx", target, ...) 본체 — KRX bulk 진입.
    Guide: legacyDate alias (date= → start=) 호환. apiKey None 시 HF fallback.
    When: GatherEntry._run("krx", target|"close", ...) lookup 시.
    How: krx.krxApi.gatherKrx(target, start, end, market) 위임.

    legacyDate alias (date= → start=) 호환 처리.

    Args:
        g: 무시 (gatherKrx 직접 호출).
        target: 컬럼명 (close/rsi14 등). None 이면 "close".
        market: "KR" / "KOSPI" / "KOSDAQ".
        start/end: ISO date.
        marketExplicit: 무시.
        **kwargs: apiKey, stockCodes, date (legacy → start).

    Returns:
        pl.DataFrame — wide pivot (행=종목, 열=일자).

    Raises:
        외부 API 오류 (gatherKrx 가 던지는 ValueError).

    Example::

        df = handleKrx(g, "close", market="KR", start="2024-01-01", end=None, marketExplicit=False)

    Requires:
        ``krx.krxApi.gatherKrx`` import 가능. apiKey 미명시 시 HF dataset fallback.

    See Also:
        main.GatherEntry._run : dispatch caller.
        krx.krxApi.gatherKrx : 위임 대상.
        handleKrxIndex : 시장군 지수 axis 동행.
    """
    from dartlab.gather.krx.krxApi import gatherKrx

    apiKey = kwargs.pop("apiKey", None)
    stockCodes = kwargs.pop("stockCodes", None)
    legacyDate = kwargs.pop("date", None)
    if legacyDate is not None and start is None:
        start = legacyDate
    return gatherKrx(
        target or "close",
        start=start,
        end=end,
        market=market,
        stockCodes=stockCodes,
        apiKey=apiKey,
    )


def handleKrxIndex(
    g: Any,  # noqa: ARG001 — gatherKrxIndex 직접 호출
    target: str | None,
    *,
    market: str,
    start: str | None,
    end: str | None,
    marketExplicit: bool,  # noqa: ARG001
    **kwargs: Any,
) -> pl.DataFrame:
    """krxIndex axis dispatch — 시장군별 전체 지수 패키지.

    Capabilities: target/market → gatherKrxIndex → 지수 wide DataFrame.
    AIContext: gather("krxIndex", ...) 본체 — KOSPI/KOSDAQ 지수 분석 진입.
    Guide: indexMarket alias (market= → 지수 그룹). apiKey None 시 HF fallback.
    When: GatherEntry._run("krxIndex", target, ...) lookup 시.
    How: krx.krxIndex.gatherKrxIndex(target, market, start, end) 위임.

    indexMarket 인자가 entry 의 market="KR" 과 별개 — KOSPI 기본.

    Args:
        g: 무시 (gatherKrxIndex 직접 호출).
        target: 컬럼명. None 이면 "close".
        market: "KR" / "KOSPI" / "KOSDAQ" (entry 수준).
        start/end: ISO date.
        marketExplicit: 무시.
        **kwargs: apiKey, indexFilter, indicators (default "basic"), indexMarket.

    Returns:
        pl.DataFrame — 시장군 전체 지수 OHLCV + 보조지표.

    Raises:
        외부 API 오류 (gatherKrxIndex 가 던지는 ValueError).

    Example::

        df = handleKrxIndex(g, "close", market="KOSPI", start=None, end=None, marketExplicit=False)

    Requires:
        ``krx.krxIndex.gatherKrxIndex`` import 가능. apiKey idx 카테고리 권한 (명시 시).

    See Also:
        main.GatherEntry._run : dispatch caller.
        krx.krxIndex.gatherKrxIndex : 위임 대상.
        handleKrx : 종목 axis 동행.
    """
    from dartlab.gather.krx.krxIndex import gatherKrxIndex

    apiKey = kwargs.pop("apiKey", None)
    indexFilter = kwargs.pop("indexFilter", None)
    indicators = kwargs.pop("indicators", "basic")
    idxMarket = kwargs.pop("indexMarket", None) or ("KOSPI" if market in ("KR", "KOSPI") else market)
    return gatherKrxIndex(
        target or "close",
        market=idxMarket,
        start=start,
        end=end,
        apiKey=apiKey,
        indexFilter=indexFilter,
        indicators=indicators,
    )


def handleCalendar(
    g: Any,  # noqa: ARG001
    target: str | None,  # noqa: ARG001
    *,
    market: str,  # noqa: ARG001
    start: str | None,  # noqa: ARG001
    end: str | None,  # noqa: ARG001
    marketExplicit: bool,  # noqa: ARG001
    **kwargs: Any,  # noqa: ARG001
) -> pl.DataFrame:
    """calendar axis — 0.10 부터 폐기. Company.calendar() 사용 유도.

    Capabilities: 즉시 ValueError + 이주 안내 메시지.
    AIContext: 0.10 마이그레이션 가드 — gather → providers cycle 회피 책임 분리.
    Guide: 호출하면 raise. Company.calendar() 로 이주.
    When: 사용자가 옛 ``gather('calendar', ...)`` 호출 시.
    How: ValueError raise + 마이그레이션 안내 메시지.

    Args:
        g/target/market/start/end/marketExplicit/**kwargs: 모두 무시 (즉시 raise).

    Returns:
        반환 없음 — 항상 ValueError 발생.

    Requires:
        외부 의존 없음. 폐기 안내 메시지만 제공.

    Raises:
        ValueError — 항상. Company.calendar() 로 이주 안내 포함.

    Example::

        # 사용자 측 마이그레이션:
        c = dartlab.Company('005930')
        c.calendar(horizonDays=30)

    See Also:
        providers.dart.Company.calendar : 이주 대상.
    """
    raise ValueError(
        "gather('calendar') 는 0.10 부터 폐기됨. Company.calendar() 사용. "
        "예: c = dartlab.Company('005930'); c.calendar(horizonDays=30). "
        "이유: gather → providers cycle 회피 (책임 분리)."
    )


def handleNarrative(
    g: Any,  # noqa: ARG001
    target: str | None,
    *,
    market: str,
    start: str | None,
    end: str | None,
    marketExplicit: bool,  # noqa: ARG001
    **kwargs: Any,
) -> pl.DataFrame:
    """narrative axis dispatch — Phase A/B/C/D 통합 news archive 진입.

    target 분기:
        - None / "raw" / "" : raw archive (loadNewsArchive)
        - "pulse" : (date × topic) 격자 (buildNarrativePulse)
        - "score" : 12 번째 macro 축 dict → 1행 DataFrame (analyzeNarrative)
        - "topics" : top topic 랭킹 (volume + sentiment mean)
        - 6자리 숫자 : 종목명 keyword 필터 (KRX codeToName)
        - 그 외 : 자유 keyword title contains 필터

    Args:
        g: 무시 (read-only archive).
        target: 위 분기 키 또는 None.
        market: "KR" | "US".
        start/end: ISO date 또는 None. None + days 시 today-days~today.
        marketExplicit: 무시.
        **kwargs: days (default 30), asof, sentimentModel, top.

    Returns:
        pl.DataFrame — 분기별 schema.

    Raises:
        없음 — 빈 archive 면 동일 schema 빈 DataFrame.

    See Also:
        ``gather.bulkData.newsHeadlines.loadNewsArchive`` — raw archive 로더.
        ``quant.text.narrativePulse.buildNarrativePulse`` — pulse 격자.
        ``macro.narrative.narrative.analyzeNarrative`` — score 결과.
    """
    from datetime import date as _date
    from datetime import timedelta

    days = kwargs.pop("days", 30)
    asof = kwargs.pop("asof", None)
    sentimentModel = kwargs.pop("sentimentModel", "auto")
    top = kwargs.pop("top", 10)

    # start/end 기본값 — today-days~today
    if start is None and end is None:
        end_d = _date.today()
        start_d = end_d - timedelta(days=days)
        start = start_d.isoformat()
        end = end_d.isoformat()
    elif start is None:
        start = (_date.fromisoformat(end) - timedelta(days=days)).isoformat() if end else None
    elif end is None:
        end = _date.today().isoformat()

    from dartlab.gather.bulkData.newsHeadlines import loadNewsArchive

    if target is None or target in ("", "raw"):
        return loadNewsArchive(start, end, market, asof=asof)

    if target == "pulse":
        from dartlab.quant.text.narrativePulse import buildNarrativePulse

        return buildNarrativePulse(start, end, market, asof=asof, sentimentModel=sentimentModel)

    if target == "score":
        from dartlab.macro.narrative.narrative import analyzeNarrative

        result = analyzeNarrative(market=market, asOf=asof, lookbackDays=days, sentimentModel=sentimentModel)
        return pl.DataFrame([result])

    if target == "topics":
        from dartlab.quant.text.narrativePulse import buildNarrativePulse

        pulse = buildNarrativePulse(start, end, market, asof=asof, sentimentModel=sentimentModel)
        if pulse.height == 0:
            return pulse
        topic_col = "topic_label" if "topic_label" in pulse.columns else "topic_id"
        agg = pulse.group_by(topic_col).agg(
            pl.col("volume").sum().alias("volume_total")
            if "volume" in pulse.columns
            else pl.lit(0).alias("volume_total"),
            pl.col("sentiment_mean").mean().alias("sentiment_mean")
            if "sentiment_mean" in pulse.columns
            else pl.lit(0.0).alias("sentiment_mean"),
        )
        return agg.sort("volume_total", descending=True).head(top)

    # target 이 6 자리 숫자 → 종목명 resolve → keyword 필터
    keyword = target
    if target.isdigit() and len(target) == 6:
        try:
            from dartlab.gather.krx.listing.registry import codeToName

            name = codeToName(target)
            if name:
                keyword = name
        except Exception:
            pass

    arch = loadNewsArchive(start, end, market, asof=asof)
    if arch.height == 0 or "title" not in arch.columns:
        return arch
    return arch.filter(pl.col("title").str.contains(keyword, literal=True))


def handleDartDoc(
    g: Any,  # noqa: ARG001
    target: str | None,
    *,
    market: str,  # noqa: ARG001
    start: str | None,  # noqa: ARG001
    end: str | None,  # noqa: ARG001
    marketExplicit: bool,  # noqa: ARG001
    **kwargs: Any,  # noqa: ARG001
) -> pl.DataFrame:
    """dartDoc axis dispatch — DART 공시 viewer 원문 fetch.

    Capabilities: rcept_no → viewer.fetch → 공시 본문 DataFrame (section_order/title/text).
    AIContext: gather("dartDoc", rceptNo) 본체 — untrusted external 본문 마커 대상.
    Guide: API key 불필요 (무인증 viewer). target 14자리 rcept_no.
    When: GatherEntry._run("dartDoc", rceptNo) lookup 시.
    How: dart.viewer.fetch(rceptNo) → pl.DataFrame (sub-doc 목차 + 텍스트).

    Args:
        g: 무시 (viewer.fetch 직접 호출).
        target: rcept_no (14자리 수신번호). 빈 문자열/None 거부.
        market/start/end/marketExplicit/**kwargs: 무시.

    Returns:
        pl.DataFrame 또는 viewer fetch 결과 (sub-doc 본문).

    Raises:
        ValueError — target 누락 시.

    Example::

        df = handleDartDoc(None, "20240315000123", market="KR", start=None, end=None, marketExplicit=False)

    Requires:
        ``dart.viewer.fetch`` import 가능. 무인증 viewer (DART_API_KEY 불필요).
        target 14 자리 rcept_no 필수.

    See Also:
        main.GatherEntry._run : dispatch caller.
        dart.viewer.fetch : 위임 대상 — 공시 본문 sub-doc 파싱.
        formatting.wrap_external_in_result : 본문 untrusted 마커 wrap.
    """
    if not target:
        raise ValueError("gather('dartDoc') 는 rcept_no (14자리) target 필요")
    from dartlab.gather.dart.viewer import fetch as _fetchDartDoc

    return _fetchDartDoc(target)

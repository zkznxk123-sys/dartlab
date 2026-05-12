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

from typing import Any

import polars as pl

from .dispatch import INDEX_SYMBOLS, _fetchNaverIndex


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
    """
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
    """
    raise ValueError(
        "gather('calendar') 는 0.10 부터 폐기됨. Company.calendar() 사용. "
        "예: c = dartlab.Company('005930'); c.calendar(horizonDays=30). "
        "이유: gather → providers cycle 회피 (책임 분리)."
    )


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
    """
    if not target:
        raise ValueError("gather('dartDoc') 는 rcept_no (14자리) target 필요")
    from dartlab.gather.dart.viewer import fetch as _fetchDartDoc

    return _fetchDartDoc(target)

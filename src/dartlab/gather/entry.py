"""gather() 통합 진입점 — scan()과 동일한 3단계 패턴.

dartlab.gather()                       -> 가이드 (축 목록)
dartlab.gather("price", "005930")      -> 주가 시계열
dartlab.gather("flow", "005930")       -> 수급 동향
dartlab.gather("macro")                -> KR 거시지표 전체
dartlab.gather("macro", "CPI")         -> 단일 지표
dartlab.gather("news", "삼성전자")      -> 뉴스
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import polars as pl


@dataclass(frozen=True)
class _GatherAxisEntry:
    """gather 축 메타데이터."""

    label: str
    description: str
    example: str
    targetRequired: bool = True


_AXIS_REGISTRY: dict[str, _GatherAxisEntry] = {
    "price": _GatherAxisEntry(
        label="주가",
        description=(
            "OHLCV 시계열 (수정주가). "
            "KR: 네이버 차트 API (최대 12년 일봉, API 키 불필요). "
            "US/해외: Yahoo v8 → 네이버 글로벌 자동 fallback. "
            "시장 지수도 가능: gather('price', 'KOSPI')"
        ),
        example='gather("price", "005930") / gather("price", "AAPL", market="US")',
    ),
    "flow": _GatherAxisEntry(
        label="수급",
        description="외국인/기관 순매수 동향 (KR 전용, 네이버 금융). US는 미지원 → None",
        example='gather("flow", "005930")',
    ),
    "macro": _GatherAxisEntry(
        label="거시지표",
        description=(
            "KR: ECOS 한국은행 12개 지표 (API 키: ECOS_API_KEY). "
            "US: FRED 연준 25개 지표 (API 키: FRED_API_KEY). "
            "지표 미지정 시 전체 반환. 단일 지표: gather('macro', 'CPI')"
        ),
        example='gather("macro") / gather("macro", "FEDFUNDS", market="US")',
        targetRequired=False,
    ),
    "news": _GatherAxisEntry(
        label="뉴스",
        description="Google News RSS 최근 30일. API 키 불필요. 한글/영문 검색어 모두 지원",
        example='gather("news", "삼성전자") / gather("news", "AAPL")',
    ),
    "sector": _GatherAxisEntry(
        label="업종",
        description="업종 분류 + 동종업종 PER. KR: KRX KIND + 네이버 금융",
        example='gather("sector", "005930")',
    ),
    "insider": _GatherAxisEntry(
        label="내부자거래",
        description="임원/주요주주 주식 거래 내역. KR: DART API (API 키: DART_API_KEY)",
        example='gather("insider", "005930")',
    ),
    "ownership": _GatherAxisEntry(
        label="지분",
        description="기관/외국인 보유 현황 (비율+주수). KR: 네이버 금융",
        example='gather("ownership", "005930")',
    ),
    "peers": _GatherAxisEntry(
        label="피어",
        description="동종업종 피어 종목 목록 (종목코드+시총). KR: KRX/네이버",
        example='gather("peers", "005930")',
    ),
    "krx": _GatherAxisEntry(
        label="KRX 회사별 시계열",
        description=(
            "KOSPI/KOSDAQ 전종목 wide pivot — 행=stockCode+corpName, 열=일자. "
            "target (positional) 으로 raw OHLCV (close/open/high/low/volume/marketCap/...) "
            "또는 보조지표 (rsi14/ma20/ema60/macd/atr14/obv/...) 28+ 디스패치. "
            "target='raw' 면 long (KRX 원본 컬럼). "
            "apiKey 없음 (기본): HF SSOT. apiKey 명시: KRX OpenAPI 직접. 환경변수 자동 read X."
        ),
        example='gather("krx", "close", start=, end=) / gather("krx", "rsi14", start=, end=) / gather("krx", "marketCap", date=)',
        targetRequired=False,
    ),
    "krxindex": _GatherAxisEntry(
        label="KRX 지수 일별 매매현황 (시장군별 전체 지수 패키지)",
        description=(
            "KRX/KOSPI/KOSDAQ 시장군의 모든 지수 (종합/200/100/섹터/스타일/사이즈/ESG/테마) "
            "OHLCV + 거래량 + 시가총액. target=close/open/high/low/volume/marketCap/raw. "
            "indexFilter=[지수명] 으로 특정 지수 (예: KOSPI200 + 보조지표 자동). "
            "apiKey 명시 필수 — idx 카테고리 권한 별도 신청 (sto 종목 키와 분리)."
        ),
        example='gather("krxIndex", "close", market="KOSPI", start=, end=, apiKey="...")',
        targetRequired=False,
    ),
}

_ALIASES: dict[str, str] = {
    "주가": "price",
    "수급": "flow",
    "거시": "macro",
    "매크로": "macro",
    "뉴스": "news",
    "업종": "sector",
    "내부자": "insider",
    "지분": "ownership",
    "피어": "peers",
    "동종업종": "peers",
}


# 시장 지수 심볼 매핑 (네이버 차트 API 직접 수집)
_INDEX_SYMBOLS: dict[str, str] = {
    "KOSPI": "KOSPI",
    "kospi": "KOSPI",
    "코스피": "KOSPI",
    "KOSDAQ": "KOSDAQ",
    "kosdaq": "KOSDAQ",
    "코스닥": "KOSDAQ",
    "KPI200": "KPI200",
    "kpi200": "KPI200",
    "코스피200": "KPI200",
}


def _fetchNaverIndex(symbol: str, count: int = 500) -> pl.DataFrame:
    """네이버 차트 API로 시장 지수 OHLCV 수집.

    Parameters
    ----------
    symbol : str
        지수 심볼 (예: ``"KOSPI"``, ``"KOSDAQ"``, ``"KPI200"``).
    count : int
        요청 거래일 수 (일). 기본 500.

    Returns
    -------
    pl.DataFrame
        date : date — 거래일
        open : float — 시가 (포인트)
        high : float — 고가 (포인트)
        low : float — 저가 (포인트)
        close : float — 종가 (포인트)
        volume : int — 거래량 (주)
        데이터 없으면 빈 DataFrame.
    """
    import re

    import httpx

    url = f"https://fchart.stock.naver.com/sise.nhn?symbol={symbol}&timeframe=day&count={count}&requestType=0"
    r = httpx.get(url, timeout=15)
    items = re.findall(r'data="([^"]+)"', r.text)
    if not items:
        return pl.DataFrame()

    rows = []
    for item in items:
        parts = item.split("|")
        if len(parts) < 6:
            continue
        try:
            rows.append(
                {
                    "date": f"{parts[0][:4]}-{parts[0][4:6]}-{parts[0][6:8]}",
                    "open": float(parts[1]),
                    "high": float(parts[2]),
                    "low": float(parts[3]),
                    "close": float(parts[4]),
                    "volume": int(parts[5]),
                }
            )
        except (ValueError, IndexError):
            continue

    if not rows:
        return pl.DataFrame()
    return pl.DataFrame(rows).with_columns(pl.col("date").str.to_date("%Y-%m-%d"))


def _resolveAxis(axis: str) -> str:
    """축 이름/별칭 -> 정규 키.

    Parameters
    ----------
    axis : str
        축 이름 또는 한글 별칭 (예: ``"price"``, ``"주가"``).

    Returns
    -------
    str
        정규 축 키 (예: ``"price"``, ``"flow"``, ``"macro"``).

    Raises
    ------
    ValueError
        미등록 축 이름일 때.
    """
    lower = axis.lower()
    if lower in _AXIS_REGISTRY:
        return lower
    if axis in _ALIASES:
        return _ALIASES[axis]
    if lower in _ALIASES:
        return _ALIASES[lower]
    available = ", ".join(sorted(_AXIS_REGISTRY))
    raise ValueError(
        f"알 수 없는 gather 축: '{axis}'. 가용 축: {available}\n"
        f"  사용법: c.gather() 또는 dartlab.gather() 로 전체 축 가이드를 확인하세요."
    )


class GatherEntry:
    """외부 시장 데이터 통합 수집 — 8축, 전부 Polars DataFrame.

    Capabilities:
        - price: OHLCV 시계열 (KR Naver/US Yahoo, 기본 1년, 최대 6000거래일)
        - flow: 외국인/기관 수급 동향 (KR 전용, Naver)
        - macro: ECOS(KR 12개) / FRED(US 25개) 거시지표 시계열
        - news: Google News RSS 뉴스 수집 (최근 30일)
        - sector: 업종 분류 (KR KIND+Naver)
        - insider: 내부자 거래 (KR DART)
        - ownership: 기관/외국인 지분 보유 (KR Naver)
        - peers: 동종업종 피어 종목 (시총 포함, KR Naver)
        - 자동 fallback 체인, circuit breaker, TTL 캐시

    AIContext:
        - ask()/chat()에서 주가/수급/거시 데이터를 컨텍스트로 주입 가능
        - 기업 분석 시 시장 데이터 보충 자료로 활용

    Guide:
        - "주가 추이 보여줘" -> gather("price", "005930")
        - "외국인 매매 동향" -> gather("flow", "005930")
        - "금리 추이 알려줘" -> gather("macro", "BASE_RATE") 또는 gather("macro", "FEDFUNDS")
        - "최근 뉴스 찾아줘" -> gather("news", "삼성전자")
        - "업종 알려줘" -> gather("sector", "005930")
        - "내부자 거래 보여줘" -> gather("insider", "005930")
        - "지분 보유 현황" -> gather("ownership", "005930")
        - "동종업종 비교" -> gather("peers", "005930")
        - "미국 거시지표 전체" -> gather("macro", market="US") 또는 gather("US")
        - 주가+수급은 scan과 다름. scan은 재무 기반 횡단, gather는 시장 실시간.

    SeeAlso:
        - scan: 재무 기반 전종목 횡단분석 (거버넌스, 현금흐름 등)
        - Company: 개별 종목 공시/재무 데이터
        - analysis: 14축 전략분석 (재무비율, 수익구조 등)

    Args:
        axis: 축 이름 ("price", "flow", "macro", "news"). None이면 가이드 반환.
        target: 종목코드/지표코드/검색어. 축별로 다름.
        **kwargs: market ("KR"/"US"), start, end, days 등 축별 옵션.

    Returns:
        pl.DataFrame — 축별 시계열 데이터. axis=None이면 4축 가이드 DataFrame.

    Requires:
        price/flow/news: 없음 (공개 API)
        macro: API 키 — ECOS_API_KEY (KR) 또는 FRED_API_KEY (US)

    Example::

        import dartlab
        dartlab.gather()                              # 가이드
        dartlab.gather("price", "005930")             # 삼성전자 1년 OHLCV
        dartlab.gather("flow", "005930")              # 수급
        dartlab.gather("macro")                       # KR 거시 전체
        dartlab.gather("macro", "FEDFUNDS")           # 자동 US 감지
        dartlab.gather("news", "삼성전자")             # 뉴스
    """

    def __call__(
        self,
        axis: str | None = None,
        target: str | None = None,
        **kwargs: Any,
    ) -> pl.DataFrame:
        """외부 시장 데이터 수집 — 주가·수급·거시지표·뉴스 4 축.

        Parameters
        ----------
        axis : str, optional
            수집 축. None 이면 가이드 DataFrame 반환.
            "price" — OHLCV 주가, "flow" — 투자자별 수급,
            "macro" — FRED/ECOS 거시지표, "news" — Google News,
            "sector" — 업종/산업 분류, "insider" — 내부자 거래.
        target : str, optional
            종목코드/지표코드/검색어. 축에 따라 필수.
        **kwargs
            market ("KR"/"US"), start, end, days 등 축별 옵션.

        Returns
        -------
        pl.DataFrame
            axis=None (가이드):
                axis : str — 축 이름
                label : str — 한글 레이블
                description : str — 설명
                example : str — 사용 예시
            axis="price":
                date : date — 날짜
                open : float — 시가
                high : float — 고가
                low : float — 저가
                close : float — 종가
                volume : int — 거래량
            axis="flow":
                date : date — 날짜
                외국인순매수 : int — 외국인 순매수량
                기관순매수 : int — 기관 순매수량
            axis="macro":
                date : date — 날짜
                지표별 컬럼 : float — ECOS/FRED 거시지표 값
            axis="news":
                title : str — 뉴스 제목
                link : str — 기사 URL
                pubDate : str — 발행일
            axis="sector":
                sectorCode : str — 업종코드
                sectorName : str — 업종명
                industryCode : str — 산업코드
                industryName : str — 산업명
                market : str — 시장 (KR/US)
            axis="insider":
                date : str — 거래일
                name : str — 거래자명
                position : str — 직위
                tradeType : str — 거래유형
                changeShares : int — 변동 주수

        Raises
        ------
        ValueError
            축 이름이 등록되지 않은 경우.
            target 필수 축에서 target 누락 시.

        Examples
        --------
        >>> dartlab.gather()                              # 가이드
        >>> dartlab.gather("price", "005930")              # KR OHLCV
        >>> dartlab.gather("price", "AAPL", market="US")   # US 주가
        >>> dartlab.gather("macro", "FEDFUNDS")            # 미국 기준금리
        >>> dartlab.gather("news", "삼성전자")              # Google News

        Notes
        -----
        Naver(KR)/Yahoo(US)/FRED/ECOS/Google News 경유. API 키 불필요.
        결과는 Polars DataFrame — 분석 엔진 입력으로 바로 사용 가능.

        Guide
        -----
        When: 분석 엔진에 필요한 외부 데이터를 수집할 때.
        How: gather → analysis/quant 파이프라인. gather("price") 는 quant 의 데이터 원천.
            gather("macro") 는 macro 엔진과 상호 보완 (raw 데이터 vs 분석 결과).
        Verified:
            - gather("news") → 뉴스 목록 + 헤드라인 해석 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)

        See Also
        --------
        quant : 주가 기반 정량 분석 — gather("price") 데이터 소비.
        macro : 거시 분석 — gather("macro") raw 데이터의 분석 결과.
        scan : 전종목 비교 — 사전 빌드 데이터와 gather 실시간 데이터 상호 보완.
        """
        if axis is None:
            return self._guide()

        resolved = _resolveAxis(axis)
        entry = _AXIS_REGISTRY[resolved]

        if entry.targetRequired and target is None:
            raise ValueError(f'gather("{resolved}")에는 대상이 필요합니다.\n  예: {entry.example}')

        return self._run(resolved, target, **kwargs)

    def _run(self, axis: str, target: str | None, **kwargs: Any) -> pl.DataFrame:
        """축별 실행 디스패치.

        Parameters
        ----------
        axis : str
            정규 축 키 (예: ``"price"``, ``"flow"``).
        target : str | None
            종목코드/지표코드/검색어.
        **kwargs
            market, start, end, days 등 축별 옵션.

        Returns
        -------
        pl.DataFrame
            축별 시계열 데이터. 스키마는 ``__call__`` 독스트링 참조.
        """
        from dartlab.gather import getDefaultGather

        g = getDefaultGather()

        _marketExplicit = "market" in kwargs
        market = kwargs.pop("market", "KR")
        start = kwargs.pop("start", None)
        end = kwargs.pop("end", None)

        if axis == "price":
            # 시장 지수 심볼이면 네이버 차트 API 직접 수집
            if target and target in _INDEX_SYMBOLS:
                result = _fetchNaverIndex(_INDEX_SYMBOLS[target])
            else:
                result = g.price(target, market=market, start=start, end=end)
            # R30-1: 빈 DataFrame silent → 명시적 ValueError
            if result is None or (hasattr(result, "shape") and result.shape == (0, 0)):
                raise ValueError(
                    f"gather('price', '{target}') 결과가 비어 있습니다. "
                    f"종목코드/티커를 확인하세요 (market={market}). "
                    f"네트워크 또는 외부 API 일시적 오류일 수도 있습니다."
                )
            # indicators 옵션 — 단일 종목/지수 OHLCV 에 보조지표 컬럼 추가
            #   default "basic": 9 핵심 지표 자동 (사용자 편의 — 호출 한번에 분석 가능)
            #   False: raw OHLCV 만
            #   True: 30 표준 지표 모두
            #   list[str]: 지정한 지표만 (예: ["rsi14", "ma20"])
            indicators = kwargs.pop("indicators", "basic")
            if indicators == "basic":
                indicators = [
                    "sma5",
                    "sma20",
                    "sma60",
                    "ema12",
                    "ema26",
                    "rsi14",
                    "macd",
                    "atr14",
                    "obv",
                ]
            elif indicators is False:
                indicators = None
            if indicators:
                from dartlab.gather._indicatorDispatch import addIndicators

                result = addIndicators(result, indicators=indicators)
            return result
        if axis == "flow":
            return g.flow(target, market=market)
        if axis == "macro":
            if target is None:
                return g.macro(market, start=start, end=end)
            if _marketExplicit:
                return g.macro(market, target, start=start, end=end)
            return g.macro(target, start=start, end=end)
        if axis == "news":
            days = kwargs.pop("days", 30)
            return g.news(target, market=market, days=days)
        if axis == "sector":
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
        if axis == "insider":
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
        if axis == "ownership":
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
        if axis == "peers":
            peers = g.industryPeers(target, market=market)
            if not peers:
                return pl.DataFrame()
            return pl.DataFrame(peers)
        if axis == "krx":
            from dartlab.gather.krxApi import gatherKrx

            apiKey = kwargs.pop("apiKey", None)
            stockCodes = kwargs.pop("stockCodes", None)
            # date legacy alias — 단일일자 호출의 호환성 (start 로 매핑 후 폐기)
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
        if axis == "krxindex":
            from dartlab.gather.krxIndex import gatherKrxIndex

            apiKey = kwargs.pop("apiKey", None)
            indexFilter = kwargs.pop("indexFilter", None)
            indicators = kwargs.pop("indicators", "basic")
            # market 디폴트는 "KOSPI" — entry 수준 market="KR" 와 별개
            idx_market = kwargs.pop("indexMarket", None) or ("KOSPI" if market in ("KR", "KOSPI") else market)
            return gatherKrxIndex(
                target or "close",
                market=idx_market,
                start=start,
                end=end,
                apiKey=apiKey,
                indexFilter=indexFilter,
                indicators=indicators,
            )

        raise ValueError(f"미지원 gather 축: {axis}")

    def _guide(self) -> pl.DataFrame:
        """가이드 DataFrame — 축 목록 + 설명 + 사용 예시 + API 키 안내.

        Returns
        -------
        pl.DataFrame
            axis : str — 축 이름
            label : str — 한글 레이블
            description : str — 설명 (소스+제한 포함)
            example : str — 사용 예시
            apiKey : str — 필요한 API 키 (없으면 "불필요")
        """
        _API_KEY_INFO: dict[str, str] = {
            "price": "불필요",
            "flow": "불필요",
            "macro": "ECOS_API_KEY (KR) / FRED_API_KEY (US)",
            "news": "불필요",
            "sector": "불필요",
            "insider": "DART_API_KEY",
            "ownership": "불필요",
            "peers": "불필요",
            "krx": "불필요 (기본 HF SSOT, apiKey 명시 시 KRX OpenAPI 직접 호출)",
        }
        rows = [
            {
                "axis": key,
                "label": entry.label,
                "description": entry.description,
                "example": entry.example,
                "apiKey": _API_KEY_INFO.get(key, "불필요"),
            }
            for key, entry in _AXIS_REGISTRY.items()
        ]
        return pl.DataFrame(rows)

    def _apiKeyGuide(self) -> str:
        """API 키 설정 안내 문자열.

        Returns
        -------
        str
            .env 설정 방법 + 발급 링크.
        """
        return (
            "━━━ API 키 설정 안내 ━━━\n"
            "\n"
            "거시지표(macro)와 내부자거래(insider)는 API 키가 필요합니다.\n"
            ".env 파일에 아래 키를 추가하세요:\n"
            "\n"
            "  ECOS_API_KEY=발급키     # 한국은행 ECOS (KR 거시지표)\n"
            "  FRED_API_KEY=발급키     # 미국 연준 FRED (US 거시지표)\n"
            "  DART_API_KEY=발급키     # 금융감독원 DART (내부자거래)\n"
            "\n"
            "발급 링크:\n"
            "  ECOS: https://ecos.bok.or.kr/api/#/DevGuide/StatisticalCodeSearch\n"
            "  FRED: https://fred.stlouisfed.org/docs/api/api_key.html\n"
            "  DART: https://opendart.fss.or.kr/uss/uia/egovLoginUss498.do\n"
        )

    def __repr__(self) -> str:
        lines = [
            f"Gather — {len(_AXIS_REGISTRY)}축 외부 시장 데이터 수집",
            "",
            "━━━ 축 목록 ━━━",
        ]
        for key, entry in _AXIS_REGISTRY.items():
            lines.append(f"  {key:12s} {entry.label} — {entry.description[:60]}")
        lines.append("")
        lines.append("━━━ 빠른 시작 ━━━")
        lines.append("  dartlab.gather()                        # 이 가이드")
        lines.append('  dartlab.gather("price", "005930")       # 삼성전자 주가')
        lines.append('  dartlab.gather("price", "AAPL", market="US")  # 미국 주가')
        lines.append('  dartlab.gather("macro")                 # KR 거시지표 전체')
        lines.append('  dartlab.gather("news", "삼성전자")       # 뉴스')
        lines.append("")
        lines.append("━━━ 시장 지수 ━━━")
        lines.append('  dartlab.gather("price", "KOSPI")        # 코스피 지수')
        lines.append('  dartlab.gather("price", "KOSDAQ")       # 코스닥 지수')
        lines.append("")
        lines.append("━━━ API 키 필요 ━━━")
        lines.append("  macro: ECOS_API_KEY (KR) / FRED_API_KEY (US)")
        lines.append("  insider: DART_API_KEY")
        lines.append("  → dartlab.gather._apiKeyGuide() 로 발급 링크 확인")
        lines.append("")
        lines.append(
            "노트북: https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/02_gather.py"
        )
        return "\n".join(lines)

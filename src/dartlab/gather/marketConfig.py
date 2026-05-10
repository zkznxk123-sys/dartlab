"""시장별 메타데이터 — ticker 변환 + fallback 체인 + 거래시간."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MarketConfig:
    """시장 중앙 설정."""

    code: str  # "KR", "US", "JP"
    name: str  # "한국", "미국"
    currency: str  # "KRW", "USD"
    exchange_suffix: str  # ".KS", "", ".T"
    benchmark_ticker: str  # "^KS11", "^GSPC"
    fallback_chain: tuple[str, ...]  # ("naver", "naver_global")
    trading_hours_utc: tuple[int, int]  # (start_hour, end_hour)


# ══════════════════════════════════════
# 시장 레지스트리
# ══════════════════════════════════════

MARKETS: dict[str, MarketConfig] = {
    "KR": MarketConfig(
        code="KR",
        name="한국",
        currency="KRW",
        exchange_suffix=".KS",
        benchmark_ticker="^KS11",
        fallback_chain=("naver", "naver_global"),
        trading_hours_utc=(0, 6),
    ),
    "US": MarketConfig(
        code="US",
        name="미국",
        currency="USD",
        exchange_suffix="",
        benchmark_ticker="^GSPC",
        fallback_chain=("yahoo_chart", "naver_global", "fmp"),
        trading_hours_utc=(14, 21),
    ),
    "JP": MarketConfig(
        code="JP",
        name="일본",
        currency="JPY",
        exchange_suffix=".T",
        benchmark_ticker="^N225",
        fallback_chain=("yahoo_chart", "naver_global", "fmp"),
        trading_hours_utc=(0, 6),
    ),
    "HK": MarketConfig(
        code="HK",
        name="홍콩",
        currency="HKD",
        exchange_suffix=".HK",
        benchmark_ticker="^HSI",
        fallback_chain=("yahoo_chart", "naver_global", "fmp"),
        trading_hours_utc=(1, 8),
    ),
    "UK": MarketConfig(
        code="UK",
        name="영국",
        currency="GBP",
        exchange_suffix=".L",
        benchmark_ticker="^FTSE",
        fallback_chain=("yahoo_chart", "naver_global", "fmp"),
        trading_hours_utc=(8, 16),
    ),
    "DE": MarketConfig(
        code="DE",
        name="독일",
        currency="EUR",
        exchange_suffix=".DE",
        benchmark_ticker="^GDAXI",
        fallback_chain=("yahoo_chart", "naver_global", "fmp"),
        trading_hours_utc=(7, 16),
    ),
    "CN": MarketConfig(
        code="CN",
        name="중국",
        currency="CNY",
        exchange_suffix=".SS",
        benchmark_ticker="000001.SS",
        fallback_chain=("yahoo_chart", "naver_global", "fmp"),
        trading_hours_utc=(1, 7),
    ),
    "IN": MarketConfig(
        code="IN",
        name="인도",
        currency="INR",
        exchange_suffix=".NS",
        benchmark_ticker="^NSEI",
        fallback_chain=("yahoo_chart", "naver_global", "fmp"),
        trading_hours_utc=(4, 10),
    ),
}

# 심천 거래소 종목 접미사 (상하이 .SS가 기본)
_CN_SZ_PREFIXES = ("00", "30")


def getMarketConfig(market: str) -> MarketConfig:
    """시장 코드 → MarketConfig.

    consistency_no_alias 원칙: case-insensitive 매칭 (``market.upper()``) 은
    silent alias 라 인정하지 않는다. 신뢰성 원칙: 미등록 market 을 silent 하게
    US 로 reroute 하지 않고 ValueError 로 명시 — 사용자 typo 가 잘못된 시장
    데이터로 흘러가는 사고 차단.

    Parameters
    ----------
    market : str
        시장 코드 정식 표기 (대문자, ISO 3166 alpha-2 스타일). 예: ``"KR"``,
        ``"US"``, ``"JP"``, ``"HK"``, ``"CN"``, ``"IN"``.

    Returns
    -------
    MarketConfig
        해당 시장 설정.

    Raises
    ------
    ValueError
        미등록 시장 또는 case 불일치 (예: ``"kr"``, ``"Us"``).
    """
    if market not in MARKETS:
        available = ", ".join(sorted(MARKETS))
        raise ValueError(
            f"알 수 없는 시장 코드: '{market}'. 가용 시장: {available}\n"
            f"  정식 표기 (대문자) 를 사용하세요. 예: market='KR'."
        )
    return MARKETS[market]


def resolveTicker(stockCode: str, market: str, source: str) -> str:
    """stock_code + market + source → 소스별 ticker 문자열.

    - naver: 종목코드 그대로 (KR only)
    - naver_global: 종목코드 + 거래소 접미사
    - fmp: 종목코드 + 거래소 접미사 (Yahoo와 동일 형식)

    Parameters
    ----------
    stock_code : str
        종목코드/티커 (예: "005930", "AAPL", "7203").
    market : str
        시장 코드 ("KR", "US", "JP", "HK", "CN" 등).
    source : str
        데이터 소스 이름 ("naver", "naver_global", "fmp", "yahoo_chart" 등).

    Returns
    -------
    str
        소스에 맞게 변환된 ticker 문자열.
        예: "7203.T" (JP/yahoo_chart), "0293.HK" (HK), "005930" (KR/naver).
    """
    config = getMarketConfig(market)

    # naver는 KR 종목코드를 그대로 사용
    if source == "naver":
        return stockCode

    # US는 접미사 없음
    if market == "US":
        return stockCode

    # CN 심천 거래소 분기
    if market == "CN":
        for prefix in _CN_SZ_PREFIXES:
            if stockCode.startswith(prefix):
                return f"{stockCode}.SZ"
        return f"{stockCode}.SS"

    # HK: 4자리 패딩 (Yahoo는 0293.HK 형식)
    if market == "HK" and stockCode.isdigit():
        return f"{stockCode.zfill(4)}{config.exchange_suffix}"

    return f"{stockCode}{config.exchange_suffix}"

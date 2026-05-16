"""매크로 심리 분석 — 공포탐욕 근사 + VIX 구간."""

from __future__ import annotations

from dataclasses import dataclass

from dartlab.macro.cycles.macroCycle import classifyVixRegime
from dartlab.macro.seriesFetch import (
    applyOverrides,
    collectTimeseries,
    fetchChangePct,
    fetchLatest,
    fetchSeriesList,
    getGather,
)

# ══════════════════════════════════════
# 데이터 구조
# ══════════════════════════════════════


@dataclass(frozen=True)
class SentimentScore:
    """시장 심리 지수 (CNN Fear & Greed 근사)."""

    score: float  # 0-100 (0=극단공포, 100=극단탐욕)
    zone: str  # "extreme_fear" | "fear" | "neutral" | "greed" | "extreme_greed"
    zoneLabel: str  # "극단공포" | "공포" | "중립" | "탐욕" | "극단탐욕"
    components: dict[str, float]  # 개별 요소 점수


@dataclass(frozen=True)
class RateExpectation:
    """시장 금리 기대 방향 (FedWatch 근사)."""

    spread2yFf: float  # 2Y - Fed Funds 스프레드 (%p)
    spread10y2y: float | None  # 10Y - 2Y 스프레드 (%p)
    direction: str  # "cut_expected" | "hike_expected" | "hold_expected"
    directionLabel: str  # "인하 기대" | "인상 기대" | "동결 기대"
    strength: str  # "strong" | "moderate" | "mild"


@dataclass(frozen=True)
class EmploymentSignal:
    """고용 상태 해석."""

    state: str  # "strong" | "moderate" | "weakening" | "weak"
    stateLabel: str  # "강함" | "보통" | "약화" | "약함"
    reasoning: tuple[str, ...]


@dataclass(frozen=True)
class InflationSignal:
    """물가 상태 해석."""

    state: str  # "hot" | "warm" | "target" | "cool" | "cold"
    stateLabel: str  # "과열" | "높음" | "목표부근" | "둔화" | "디플레우려"
    reasoning: tuple[str, ...]


# ══════════════════════════════════════
# 공포탐욕 근사
# ══════════════════════════════════════


def _normalize(value: float, low: float, high: float) -> float:
    """value를 [low, high] 범위에서 0-100으로 정규화."""
    if high <= low:
        return 50.0
    clamped = max(low, min(high, value))
    return (clamped - low) / (high - low) * 100


def calcFearGreedProxy(
    vix: float,
    sp500VsMa125: float,
    hySpread: float,
    goldEquityRatio: float | None = None,
    cryptoMomentum: float | None = None,
) -> SentimentScore:
    """FRED 4~5 요소로 CNN Fear & Greed Index 근사 — 0=극단공포 / 100=극단탐욕.

    Capabilities:
        VIX (변동성) + S&P500 모멘텀 + HY 스프레드 + (옵션) 금/주식 비율 +
        (옵션) 비트코인 모멘텀을 정규화하여 0~100 sentiment score 산출. CNN
        Fear & Greed 의 공개 데이터 기반 근사 (실제 CNN 모델은 비공개).

    Args:
        vix: CBOE VIX (낮을수록 탐욕).
        sp500VsMa125: S&P500 현재가 / 125 일 이동평균 비율 (1.0=평균, >1=탐욕).
        hySpread: HY 스프레드 (bps, 낮을수록 탐욕).
        goldEquityRatio: 금 / S&P500 비율. 높을수록 공포. None 이면 제외.
        cryptoMomentum: BTC 90 일 변화율 (%). 양수=탐욕, 음수=공포. None 이면 제외.

    Returns:
        ``SentimentScore`` — ``score`` (0~100 float) + ``label`` (str) +
        ``components`` (dict[str, float]) 의 dataclass.

    Example:
        >>> from dartlab.macro.cycles.sentiment import calcFearGreedProxy
        >>> r = calcFearGreedProxy(vix=35.0, sp500VsMa125=-10.0, hySpread=8.0)
        >>> r.score
        15.5

    Guide:
        Sentiment 단일 지표 의존 금지 — 사이클 + 위기 + 예측과 함께 해석.
        score < 25 은 극단 공포 (역사적 매수 zone), > 75 은 극단 탐욕 (조심).
        crypto 모멘텀은 2020+ 의 강력한 risk-on/off 신호.

    SeeAlso:
        - ``calcSentiment``: 종합 sentiment (본 함수 + 추가 신호 통합)
        - ``classifyVixRegime``: VIX 단독 regime 판별
        - CNN Fear & Greed Index 공식 페이지

    Requires:
        FRED 시리즈 VIXCLS + S&P500 + BAMLH0A0HYM2 (+ GOLDAMGBD228NLBM
        옵션). API key 불필요.

    AIContext:
        "시장 심리 과열인가" · "공포 / 탐욕 어느 쪽" · "매수 zone 인가" 등
        심리 지표 질문에 호출. score + components 둘 다 인용.

    LLM Specifications:
        AntiPatterns:
            - score 만 인용 (components 분해 무시) — VIX 만 극단인지 모두 극단인지 다름
            - cryptoMomentum 절대값 큰데 None 처리 — 2020+ 환경에선 포함 권장
            - 1 일치 score 만 보고 sentiment 단정 — 추세 (5/20 일 평균) 권장
        OutputSchema:
            ``SentimentScore(score: float, label: str, components: dict[str, float])``.
            components 키: ``vix``/``momentum``/``credit``/``safe_haven``?/``crypto``?.
        Prerequisites:
            없음 (순수 함수). 입력 3~5 float 만.
        Freshness:
            VIX 일간, S&P500 일간, HY 스프레드 일간 — 동일 일자 동기화 권장.
        Dataflow:
            (vix, sp500vsMa, hySpread, gold?, crypto?) → _normalize 5 요소
            → 가중 평균 → SentimentScore.
        TargetMarkets: US (FRED). KR 미지원.
    """
    components: dict[str, float] = {}

    # VIX: 10(극단탐욕) ~ 40(극단공포) → 반전
    components["vix"] = 100 - _normalize(vix, 10, 40)

    # S&P500 모멘텀: 0.9(공포) ~ 1.1(탐욕)
    components["momentum"] = _normalize(sp500VsMa125, 0.90, 1.10)

    # HY 스프레드: 300(탐욕) ~ 700(공포) → 반전
    components["credit"] = 100 - _normalize(hySpread, 300, 700)

    # 금/주식 비율 (선택): 높으면 공포
    if goldEquityRatio is not None:
        components["safe_haven"] = 100 - _normalize(goldEquityRatio, 0.3, 0.6)

    # 비트코인 모멘텀 (선택): 유동성 과잉/긴축의 극단 지표
    # -30%(공포) ~ +50%(탐욕) 범위 정규화
    if cryptoMomentum is not None:
        components["crypto"] = _normalize(cryptoMomentum, -30, 50)

    score = sum(components.values()) / len(components)
    score = max(0, min(100, score))

    if score < 25:
        zone, label = "extreme_fear", "극단공포"
    elif score < 45:
        zone, label = "fear", "공포"
    elif score < 55:
        zone, label = "neutral", "중립"
    elif score < 75:
        zone, label = "greed", "탐욕"
    else:
        zone, label = "extreme_greed", "극단탐욕"

    return SentimentScore(
        score=round(score, 1),
        zone=zone,
        zoneLabel=label,
        components={k: round(v, 1) for k, v in components.items()},
    )


# ══════════════════════════════════════
# 금리 기대 (FedWatch 근사)
# ══════════════════════════════════════


def estimateRateExpectation(
    ffRate: float,
    dgs2: float,
    dgs10: float | None = None,
) -> RateExpectation:
    """2Y-FF 스프레드로 시장 금리 기대 방향 근사.

    2Y 국채는 향후 2년간 정책금리 경로 기대를 반영.
    2Y < FF → 시장은 인하를 기대.
    2Y > FF → 시장은 인상을 기대.

    Args:
        ff_rate: Fed Funds Rate (%)
        dgs2: 2년 국채 수익률 (%)
        dgs10: 10년 국채 수익률 (%) — optional, 기울기 정보용

    Returns:
        RateExpectation
    """
    spread = dgs2 - ffRate
    spread_10y2y = (dgs10 - dgs2) if dgs10 is not None else None

    if spread < -0.50:
        direction, label, strength = "cut_expected", "인하 기대", "strong"
    elif spread < -0.25:
        direction, label, strength = "cut_expected", "인하 기대", "moderate"
    elif spread < -0.10:
        direction, label, strength = "cut_expected", "인하 기대", "mild"
    elif spread > 0.50:
        direction, label, strength = "hike_expected", "인상 기대", "strong"
    elif spread > 0.25:
        direction, label, strength = "hike_expected", "인상 기대", "moderate"
    elif spread > 0.10:
        direction, label, strength = "hike_expected", "인상 기대", "mild"
    else:
        direction, label, strength = "hold_expected", "동결 기대", "moderate"

    return RateExpectation(
        spread2yFf=round(spread, 3),
        spread10y2y=round(spread_10y2y, 3) if spread_10y2y is not None else None,
        direction=direction,
        directionLabel=label,
        strength=strength,
    )


# ── interpretEmployment + interpretInflation + ismAssetAllocation + krInflationModel → _sentimentRegional.py 분리 ──

from dartlab.macro.cycles._sentimentRegional import (  # noqa: E402, F401
    ISMAllocationSignal,
    KRInflationEstimate,
    interpretEmployment,
    interpretInflation,
    ismAssetAllocation,
    krInflationModel,
)


def _fetchSentimentData(market: str, asOf: str | None = None) -> dict[str, float | None]:
    """gather에서 심리 지표 수집.

    Parameters
    ----------
    market : str
        ``"US"`` | ``"KR"``.
    as_of : str | None
        기준일. ``None`` 이면 최신.

    Returns
    -------
    dict[str, float | None]
        가능한 키:

        - vix : float — VIX 지수 (pt)
        - sp500_vs_ma125 : float — S&P 500 / 125일 이평 비율 (배)
        - hy_spread : float — HY 스프레드 (bp)
        - gold_equity_ratio : float — 금/S&P 500 비율 (배)
        - crypto_momentum : float — BTC 90일 변화율 (%)
    """
    g = getGather(asOf)
    data: dict[str, float | None] = {}

    data["vix"] = fetchLatest(g, "VIXCLS")

    sp_list = fetchSeriesList(g, "SP500")
    if sp_list and len(sp_list) >= 125:
        current = sp_list[-1]
        ma125 = sum(sp_list[-125:]) / 125
        if ma125 > 0:
            data["sp500_vs_ma125"] = current / ma125

    hy = fetchLatest(g, "BAMLH0A0HYM2")
    if hy is not None:
        data["hy_spread"] = hy * 100

    gold = fetchLatest(g, "IR14270")
    sp = fetchLatest(g, "SP500")
    if gold is not None and sp is not None and sp > 0:
        data["gold_equity_ratio"] = gold / sp

    # BTC 90일 모멘텀 — 위험자산 선호도의 극단 지표
    btc_chg = fetchChangePct(g, "CBBTCUSD", 90)
    if btc_chg is not None:
        data["crypto_momentum"] = btc_chg

    return data


def calcSentiment(*, market: str = "US", asOf: str | None = None, overrides: dict | None = None, **kwargs) -> dict:
    """시장 심리 종합 분석 — 공포탐욕 + VIX regime + JLN 불확실성.

    Capabilities:
        VIX (옵션 내재) + S&P 500 vs MA125 + HY spread 합성 → CNN 공포탐욕
        근사 score (0~100, 5 components). VIX 구간 판정 (extreme_fear/fear/
        neutral/greed/extreme_greed) + buySignal (역설지표). JLN Macro
        Uncertainty (Jurado-Ludvigson-Ng 2015 AER, 132 시계열 예측오차 기반
        실물 불확실성) 와 VIX 의 분기 추적.

    Args:
        market: "US" | "KR".
        asOf: 기준일. None 시 최신.
        overrides: 지표 강제 치환 (예: ``{"vix": 35}``).

    Returns:
        dict:
            - ``fearGreed`` (dict | None): score + zone + components.
            - ``vixRegime`` (dict | None): level + zone + buySignal.
            - ``macroUncertainty`` (dict | None): JLN value + vsVix.
            - ``timeseries`` (dict): vix / sp500 / hy_spread.

    Raises:
        없음.

    Example:
        >>> r = calcSentiment(market="US")
        >>> r["fearGreed"]["zone"], r["vixRegime"]["level"]
        ('extreme_fear', 35.2)  # 역설적으로 buySignal=True

    Guide:
        - fearGreed score 25 미만 (extreme_fear) = 역설지표 매수 신호.
        - score 75 초과 (extreme_greed) = 과열 (매도 신호 가능).
        - JLN >> VIX 차이 큼 = 실물경제 불확실성 > 금융 (recession 전조 가능).
        - VIX 30+ 가 6 개월 지속 = 위험회피 regime.

    SeeAlso:
        - ``calcFearGreedProxy``: 5 컴포넌트 단독
        - ``classifyVixRegime``: VIX 구간 라벨
        - ``calcLiquidity``: HY spread 함께

    Requires:
        FRED VIX (VIXCLS) + S&P 500 + HY OAS + (옵션) JLN.

    AIContext:
        score + zone + 핵심 component 함께. extreme zone 은 역설 신호일 수
        있어 단정 금지. JLN > VIX 이면 실물 우려 명시.

    LLM Specifications:
        AntiPatterns:
            - VIX 단독으로 sentiment 단정 — 5 컴포넌트 합성 결과 사용.
            - extreme_fear 를 "위험" 단정 — buySignal=True 인 역설지표.
        OutputSchema:
            ``{market, fearGreed: dict?, vixRegime: dict?, macroUncertainty:
              dict?, timeseries: dict}``.
        Prerequisites:
            FRED VIXCLS + SP500 + HY OAS + (JLN optional).
        Freshness:
            일별 (VIX/SP500), 월별 (JLN).
        Dataflow:
            VIX + SP500 vs MA125 + HY → fearGreed → VIX regime → JLN 별도.
        TargetMarkets: US (FRED), KR (KOSPI 변동성).
    """
    data = _fetchSentimentData(market, asOf=asOf)
    if overrides:
        data = applyOverrides(data, overrides)
    result: dict = {"market": market.upper()}

    vix = data.get("vix")
    sp_ratio = data.get("sp500_vs_ma125")
    hy = data.get("hy_spread")
    if vix is not None and sp_ratio is not None and hy is not None:
        fg = calcFearGreedProxy(
            vix,
            sp_ratio,
            hy,
            goldEquityRatio=data.get("gold_equity_ratio"),
            cryptoMomentum=data.get("crypto_momentum"),
        )
        result["fearGreed"] = {
            "score": fg.score,
            "zone": fg.zone,
            "zoneLabel": fg.zoneLabel,
            "components": fg.components,
        }
    else:
        result["fearGreed"] = None

    if vix is not None:
        vr = classifyVixRegime(vix)
        result["vixRegime"] = {"level": vr.level, "zone": vr.zone, "zoneLabel": vr.zoneLabel, "buySignal": vr.buySignal}
    else:
        result["vixRegime"] = None

    g = getGather(asOf)
    result["timeseries"] = collectTimeseries(g, {"vix": "VIXCLS", "sp500": "SP500", "hy_spread": "BAMLH0A0HYM2"})

    # ── JLN Macro Uncertainty Index — Jurado, Ludvigson, Ng (2015) AER ──
    # VIX = 금융 불확실성 (옵션 내재), JLN = 실물 불확실성 (132개 시계열 예측오차)
    try:
        jln = fetchLatest(g, "WLEMUINDXD")
        if jln is not None:
            if jln < 0.8:
                zone, zone_label = "low", "낮음"
            elif jln < 1.0:
                zone, zone_label = "moderate", "보통"
            elif jln < 1.2:
                zone, zone_label = "high", "높음"
            else:
                zone, zone_label = "extreme", "극단"

            # VIX-JLN 괴리 감지
            vix_high = vix is not None and vix > 25
            vix_low = vix is not None and vix < 15
            jln_high = jln > 1.0
            jln_low = jln < 0.8
            if (vix_high and jln_low) or (vix_low and jln_high):
                vs_vix = "divergent"
                vs_desc = "금융(VIX)과 실물(JLN) 불확실성이 괴리"
            else:
                vs_vix = "aligned"
                vs_desc = "금융과 실물 불확실성 방향 일치"

            result["macroUncertainty"] = {
                "value": round(jln, 3),
                "zone": zone,
                "zoneLabel": zone_label,
                "vsVix": vs_vix,
                "description": f"실물 불확실성 {jln:.3f} ({zone_label}). {vs_desc}.",
            }
    except (KeyError, ValueError, TypeError, AttributeError):
        pass

    return result

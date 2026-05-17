"""확장 기술적 분석 — 신호, 베타, 괴리, 리스크, 플래그.

quant 독립 엔진의 확장 모듈. OHLCV + 재무 등급 교차검증.
story 6막 서사에서 시장분석 섹션이 이 함수들을 소비한다.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl

from dartlab.core.memory import memoizedCalc as _memoized_calc
from dartlab.core.polarsUtil import isEmptyDf
from dartlab.quant.screen._extendedCache import (
    _benchmarkMetaForCompany,
    _detectMarket,
    _fetchBenchmarkForCompany,
    _fetchOhlcv,
    _isUSD,
)
from dartlab.quant.screen._extendedNarrative import (
    calcActionableTargets,
    calcCrosscheckData,
    calcQuantConclusionData,
    calcRiskData,
    calcSignalData,
    calcStrategyData,
    calcStrategySnapshot,
    calcTrendData,
)

__all_helpers__ = [
    "_benchmarkMetaForCompany",
    "_detectMarket",
    "_fetchBenchmarkForCompany",
    "_fetchOhlcv",
    "_isUSD",
    "calcActionableTargets",
    "calcCrosscheckData",
    "calcQuantConclusionData",
    "calcRiskData",
    "calcSignalData",
    "calcStrategyData",
    "calcStrategySnapshot",
    "calcTrendData",
]


# ── 독립 함수 (Company 또는 raw OHLCV 모두 지원) ──


@_memoized_calc
def calcTechnicalVerdict(company) -> dict | None:
    """Company OHLCV → 기술적 종합 판단 + 25 지표 (강세/중립/약세).

    Capabilities:
        Company 의 OHLCV (gather("price") 자동 수집) 를 ``technicalVerdict`` 에
        통과시켜 RSI/ADX/MACD/볼린저/카테고리 + 시장 대비 베타·상대강도까지
        단일 dict 로 반환. quant 시장 분석의 핵심 진입점.

    Args:
        company: Company 객체. ``stockCode``, ``currency``, ``benchmark``
            (선택), ``benchmarkMode`` (선택) 속성 사용.

    Returns:
        dict | None: 다음 키 (OHLCV 30 봉 미만 시 ``None``):
            - ``verdict`` (str): ``"강세"``/``"중립"``/``"약세"``
            - ``score`` (int): -4 ~ +4
            - ``rsi`` (float): 최신 RSI(14)
            - ``adx`` (float|None): 최신 ADX(14)
            - ``aboveSma20``/``aboveSma60`` (bool|None): MA 위치
            - ``bbPosition`` (float|None): 볼린저 %B (0~100)
            - ``signals`` (dict): goldenCross/rsiSignal/macdSignal 최근 20봉 누적
            - ``relativeStrength`` (float|None): 종목 RSI - 시장 RSI
            - ``beta`` (dict|None): OLS β + α + R² + CAPM
            - ``categories`` (dict): trend 카테고리 + indicators
            - ``benchmarkUsed`` (dict|None): 사용된 벤치마크 메타

    Raises:
        없음 — 모든 예외 내부 catch → ``None``.

    Example:
        >>> from dartlab import Company
        >>> r = calcTechnicalVerdict(Company("005930"))
        >>> r["verdict"], r["score"]
        ('강세', 3)

    Guide:
        Company-bound 호출이 표준 (``c.quant("판단")``). 벤치마크 자동 선택:
        KR 종목 → KOSPI, US 종목 → S&P 500. ``benchmark`` 명시 시 override.

    See Also:
        - ``technicalVerdict``: 본 함수의 raw OHLCV 버전 (analyzer.py)
        - ``calcMarketBeta``: β 단독 계산
        - ``calcTechnicalSignals``: 최근 신호만

    When:
        ``Company.quant("판단")`` 진입점. AI 종합 기술적 판단 답변 1 차.

    How:
        company → _fetchOhlcv → technicalVerdict (RSI/ADX/MACD/BB + β/α) → dict
        합성 → memoized.

    Requires:
        gather("price") 자동 수집 가능 (네트워크). 30 봉 이상.

    AIContext:
        verdict + score 만 인용 금지 — categories.trend + rsi/adx 도 함께 노출
        해 근거 투명화. confidence 가 별도 키 없으므로 score 절댓값으로 대체.

    LLM Specifications:
        AntiPatterns:
            - OHLCV 30 봉 미만 종목 (신규 상장) 에서 verdict 인용 금지 — None.
            - benchmark="S&P500" 으로 호출하면서 market 미지정 시 KR 종목이면
              자동 감지 (market="auto") 가 KR 로 가버려 오작동.
        OutputSchema:
            ``{verdict, score, rsi, adx, aboveSma20, aboveSma60, bbPosition,
            signals, relativeStrength, beta, categories, benchmarkUsed}``.
        Prerequisites:
            ``_fetchOhlcv`` 성공 (네트워크) + 30 봉 이상.
        Freshness:
            OHLCV cache (T+1). 첫 호출 후 Company._cache 재사용.
        Dataflow:
            company → _fetchOhlcv → technicalVerdict (analyzer.py) →
            dict (verdict/score/카테고리/베타) → memoized.
        TargetMarkets: KR (Naver), US (Yahoo).
    """
    ohlcv = _fetchOhlcv(company)
    if isEmptyDf(ohlcv) or len(ohlcv) < 30:
        return None

    from dartlab.quant.signal.analyzer import technicalVerdict

    verdict = technicalVerdict(
        ohlcv,
        stockCode=getattr(company, "stockCode", None),
        market=_detectMarket(company),
        benchmark=getattr(company, "benchmark", None),
        benchmarkMode=getattr(company, "benchmarkMode", "market"),
    )
    if not verdict:
        return None

    return verdict


@_memoized_calc
def calcTechnicalSignals(company) -> dict | None:
    """최근 20일 매매 신호 요약.

    Capabilities:
        - 골든크로스/RSI/MACD/볼린저 4 신호 일괄 계산 + 최근 20 봉 누적
        - recentEvents 10 개 (날짜/타입/방향) + bullish/bearish 요약

    Args:
        company: Company 객체 (gather("price")로 OHLCV 자동 수집).

    Returns:
        dict | None — signals/signalSummary/recentEvents. OHLCV ≥ 60 일 부족 시 None.

    Guide:
        story 6 막 signal 박스 + AI 단기 매매 신호 답변 표준 출처.

    When:
        Story signal + AI 최근 신호 답변.

    How:
        ``_fetchOhlcv`` → vrsi/vgoldenCross/vrsiSignal/vmacdSignal/vbollingerSignal 동시
        → 최근 20 봉 sum + recent event 리스트.

    Requires:
        OHLCV ≥ 60 봉.

    Raises:
        없음.

    Example:
        >>> r = calcTechnicalSignals(company)
        >>> r["signalSummary"]
        {'bullish': 5, 'bearish': 2}

    See Also:
        - signal.generator : 개별 신호 계산기
        - calcTechnicalVerdict : 종합 점수

    AIContext:
        "최근 N 일 매수 신호" 답변 시 signals 합산 + recentEvents 인용.
    """
    ohlcv = _fetchOhlcv(company)
    if isEmptyDf(ohlcv) or len(ohlcv) < 60:
        return None

    close = ohlcv["close"].to_numpy().astype(np.float64)
    ohlcv["high"].to_numpy().astype(np.float64)
    ohlcv["low"].to_numpy().astype(np.float64)

    from dartlab.quant.signal import generator as sig
    from dartlab.synth import indicators as ind

    rsi = ind.vrsi(close, 14)
    recent = min(20, len(close))

    # 신호 생성
    golden = sig.vgoldenCross(close, fast=20, slow=60)
    rsi_sig = sig.vrsiSignal(rsi)
    macd_sig = sig.vmacdSignal(close)
    bb_sig = sig.vbollingerSignal(close)

    # 최근 20일 이벤트 수집
    dates = ohlcv["date"].to_list()
    recentEvents = []
    signalDefs = [
        ("goldenCross", golden),
        ("rsiSignal", rsi_sig),
        ("macdSignal", macd_sig),
        ("bollingerSignal", bb_sig),
    ]

    for name, arr in signalDefs:
        for i in range(max(0, len(arr) - recent), len(arr)):
            val = int(arr[i])
            if val != 0:
                recentEvents.append(
                    {
                        "date": str(dates[i]) if i < len(dates) else "",
                        "type": name,
                        "direction": "매수" if val > 0 else "매도",
                    }
                )

    bullish = sum(1 for e in recentEvents if e["direction"] == "매수")
    bearish = sum(1 for e in recentEvents if e["direction"] == "매도")

    return {
        "signals": {
            "goldenCross": int(golden[-recent:].sum()),
            "rsiSignal": int(rsi_sig[-recent:].sum()),
            "macdSignal": int(macd_sig[-recent:].sum()),
            "bollingerSignal": int(bb_sig[-recent:].sum()),
        },
        "signalSummary": {"bullish": bullish, "bearish": bearish},
        "recentEvents": recentEvents[-10:],  # 최근 10개까지
    }


@_memoized_calc
def calcMarketBeta(company) -> dict | None:
    """시장 베타 + CAPM 기대수익률 + 해석.

    Capabilities:
        - OLS β + R² + CAPM 기대수익 + 벤치 대비 relativeStrength
        - β 구간별 해석 문장 (5 단계: 매우 높음/약간 높음/유사/방어/독립)

    Args:
        company: Company 객체.

    Returns:
        dict | None — value/r2/capmExpected/relativeStrength/benchmarkUsed/interpretation.
        OHLCV < 60 일 또는 벤치 없음 시 None.

    Guide:
        시장 민감도 평가. β > 1.5 = 변동성 매우 큼. R² < 0.3 = 시장 동행성 약함.

    When:
        story risk 박스 + AI 변동성 답변.

    How:
        ``_fetchOhlcv`` + ``_fetchBenchmarkForCompany`` → ``_calcBeta`` + ``_relativeStrength``
        → 해석 문장 합성.

    Requires:
        OHLCV ≥ 60 봉 + 벤치 데이터 가용.

    Raises:
        없음.

    Example:
        >>> r = calcMarketBeta(company)
        >>> r["value"], r["interpretation"]
        (1.18, '시장보다 약간 높은 변동성 (β=1.18)')

    See Also:
        - signal.analyzer._calcBeta : core
        - calcMarketRisk : ATR + β 통합

    AIContext:
        "이 종목의 베타" 답변 시 value + interpretation 인용.
    """
    ohlcv = _fetchOhlcv(company)
    if isEmptyDf(ohlcv) or len(ohlcv) < 60:
        return None

    benchmark = _fetchBenchmarkForCompany(company)
    if isEmptyDf(benchmark):
        return None

    from dartlab.quant.signal.analyzer import _calcBeta, _relativeStrength

    beta_data = _calcBeta(ohlcv, benchmark)
    if beta_data is None:
        return None

    rs = _relativeStrength(ohlcv, benchmark)

    # 해석 텍스트
    bv = beta_data["value"]
    if bv > 1.5:
        interp = f"시장 대비 {(bv - 1) * 100:.0f}% 높은 변동성 — 고위험"
    elif bv > 1.1:
        interp = f"시장보다 약간 높은 변동성 (β={bv:.2f})"
    elif bv > 0.9:
        interp = f"시장과 유사한 변동성 (β={bv:.2f})"
    elif bv > 0.5:
        interp = f"시장보다 낮은 변동성 — 방어적 (β={bv:.2f})"
    else:
        interp = f"시장과 독립적 움직임 (β={bv:.2f})"

    return {
        **beta_data,
        "relativeStrength": rs,
        "benchmarkUsed": _benchmarkMetaForCompany(company),
        "interpretation": interp,
    }


@_memoized_calc
def calcFundamentalDivergence(company, *, basePeriod: str | None = None) -> dict | None:
    """재무-시장 괴리 진단 — 교차검증의 핵심.

    재무 스코어카드 등급과 기술적 판단을 비교하여
    괴리(divergence) 여부와 진단 메시지를 반환한다.

    Capabilities:
        - 재무 등급 3 단계 (good/neutral/poor) × 기술 verdict 3 단계 (bullish/neutral/bearish)
        - 9 칸 _MATRIX 에서 divergence 키워드 (순풍/관심/괴리/위험 등) + 진단 문장 추출

    Args:
        company: Company 객체.
        basePeriod: 기준 기간. 기본 None (최신).

    Returns:
        dict | None — financialGrade/technicalVerdict/technicalScore/divergence/diagnosis/matrix.
        재무 등급 + 기술 verdict 둘 다 None 시 None.

    Guide:
        review가 두 엔진 (analysis + quant) 결과를 조합할 때 scorecard 를
        ``_cache["_calcScorecard:None"]`` 에 주입 → 본 함수가 읽음.

    When:
        story crosscheck 박스 + AI "재무 vs 기술 일치 여부" 답변.

    How:
        cache scorecard 추출 → ``technicalVerdict`` → 9 칸 매트릭스 lookup.

    Requires:
        analysis scorecard 사전 계산 (review 단계) + OHLCV ≥ 30 봉.

    Raises:
        없음.

    Example:
        >>> r = calcFundamentalDivergence(company)
        >>> r["divergence"], r["matrix"]
        ('괴리', 'good_bearish')

    See Also:
        - signal.analyzer.technicalVerdict : tech verdict
        - analysis.financial.scorecard : 재무 등급

    AIContext:
        "재무 vs 기술 진단" 답변 시 divergence + diagnosis 인용.
    """
    from dartlab.quant.signal.analyzer import technicalVerdict

    # 재무 등급: Company._cache에서 읽기 (analysis가 이미 계산했다면 재사용).
    # analysis를 직접 import하지 않는다 (L2↔L2 금지).
    # review가 두 엔진을 조합할 때 scorecard를 주입한다.
    financialGrade = None
    cache = getattr(company, "_cache", None)
    if cache is not None:
        sc = cache.get("_calcScorecard:None") or cache.get("_calcScorecard:" + str(basePeriod))
        if sc:
            financialGrade = sc.get("overallGrade") or sc.get("grade")

    # 기술적 판단
    ohlcv = _fetchOhlcv(company)
    tv = None
    if ohlcv is not None and not ohlcv.is_empty() and len(ohlcv) >= 30:
        tv = technicalVerdict(
            ohlcv,
            stockCode=getattr(company, "stockCode", None),
            market=_detectMarket(company),
            benchmark=getattr(company, "benchmark", None),
            benchmarkMode=getattr(company, "benchmarkMode", "market"),
        )

    if financialGrade is None and tv is None:
        return None

    techVerdict = tv.get("verdict") if tv else None
    techScore = tv.get("score", 0) if tv else 0

    # 재무 등급 → 3단계 분류
    _GOOD = {"A+", "A", "A-", "B+", "B"}
    _NEUTRAL = {"B-", "C+", "C"}
    finCategory = "unknown"
    if financialGrade:
        if financialGrade in _GOOD:
            finCategory = "good"
        elif financialGrade in _NEUTRAL:
            finCategory = "neutral"
        else:
            finCategory = "poor"

    # 기술적 → 3단계
    techCategory = "neutral"
    if techVerdict == "강세":
        techCategory = "bullish"
    elif techVerdict == "약세":
        techCategory = "bearish"

    # 2x3 매트릭스 진단
    _MATRIX = {
        ("good", "bullish"): ("순풍", "재무와 시장 모두 긍정적 — 기업 펀더멘털이 시장에서 인정받는 상태"),
        ("good", "neutral"): ("관심", "재무는 우량하나 시장이 아직 반영하지 않음 — 모멘텀 전환 주시"),
        ("good", "bearish"): ("괴리", "재무는 양호하나 시장은 약세 — 저평가 기회이거나 시장이 선행 반영한 리스크"),
        ("neutral", "bullish"): ("기대", "시장이 실적 개선을 선반영 — 실적 확인 필요"),
        ("neutral", "neutral"): ("균형", "재무와 시장 모두 중립적 — 방향성 모색 중"),
        ("neutral", "bearish"): ("경고", "시장이 먼저 하락 반응 — 실적 악화 가능성 주시"),
        ("poor", "bullish"): ("괴리", "기술적 반등이지만 재무 리스크 주의 — 지속 가능한 반등인지 확인 필요"),
        ("poor", "neutral"): ("관심", "실적 바닥을 탐색하는 구간 — 턴어라운드 신호 주시"),
        ("poor", "bearish"): ("위험", "재무와 시장 동반 악화 — 구조적 리스크에 노출"),
    }

    key = (finCategory, techCategory)
    divergence, diagnosis = _MATRIX.get(key, ("미정", "데이터 부족으로 교차검증 불가"))

    return {
        "financialGrade": financialGrade,
        "technicalVerdict": techVerdict,
        "technicalScore": techScore,
        "divergence": divergence,
        "diagnosis": diagnosis,
        "matrix": f"{finCategory}_{techCategory}",
    }


@_memoized_calc
def calcMarketRisk(company) -> dict | None:
    """시장 리스크 — ATR 변동성 등급 + 베타 + 상대강도.

    Capabilities:
        - 14 일 ATR + ATR/close% + 4 단계 변동성 등급 (매우 높음/높음/보통/낮음)
        - ``calcMarketBeta`` 호출 → β + relativeStrength 결합

    Args:
        company: Company 객체.

    Returns:
        dict | None — beta/atr/atrPercent/relativeStrength/volatilityGrade/price.
        OHLCV < 30 봉 부족 시 None.

    Guide:
        story risk 박스 + AI 변동성·β 통합 답변. ATR% 5%+ = 매우 높음.

    When:
        Story risk + AI 변동성/β 종합 답변.

    How:
        ``vatr`` → atrPct 계산 → volatilityGrade 분류 + ``calcMarketBeta`` 합산.

    Requires:
        OHLCV ≥ 30 봉 + 벤치 가용 (β용).

    Raises:
        없음.

    Example:
        >>> r = calcMarketRisk(company)
        >>> r["volatilityGrade"]
        '높음'

    See Also:
        - calcMarketBeta : β + capm
        - synth.indicators.vatr : ATR core

    AIContext:
        "변동성 위험" 답변 시 volatilityGrade + atrPercent + β 인용.
    """
    ohlcv = _fetchOhlcv(company)
    if isEmptyDf(ohlcv) or len(ohlcv) < 30:
        return None

    close = ohlcv["close"].to_numpy().astype(np.float64)
    high = ohlcv["high"].to_numpy().astype(np.float64)
    low = ohlcv["low"].to_numpy().astype(np.float64)

    from dartlab.synth import indicators as ind

    # ATR (변동성)
    atr = ind.vatr(high, low, close, 14)
    lastAtr = float(atr[-1]) if not np.isnan(atr[-1]) else None
    lastClose = float(close[-1])
    atrPct = round(lastAtr / lastClose * 100, 1) if lastAtr and lastClose > 0 else None

    # 변동성 등급
    if atrPct is not None:
        if atrPct >= 5.0:
            volGrade = "매우 높음"
        elif atrPct >= 3.0:
            volGrade = "높음"
        elif atrPct >= 1.5:
            volGrade = "보통"
        else:
            volGrade = "낮음"
    else:
        volGrade = None

    # 베타 + 상대강도
    betaData = calcMarketBeta(company)
    betaValue = betaData.get("value") if betaData else None
    rs = betaData.get("relativeStrength") if betaData else None

    return {
        "beta": betaValue,
        "atr": lastAtr,
        "atrPercent": atrPct,
        "relativeStrength": rs,
        "volatilityGrade": volGrade,
        "price": lastClose,
    }


@_memoized_calc
def calcMarketAnalysisFlags(company) -> list[str]:
    """시장분석 플래그 — 기술적 신호 기반 경고/기회.

    Capabilities:
        - RSI ≥ 70/≤ 30, ADX ≥ 40, BB ≥ 95/≤ 5, SMA 정/역배열, score ±3 신호별 한 줄 플래그
        - ⚠ 마커로 경고/기회 시각 구분

    Args:
        company: Company 객체.

    Returns:
        list[str] — 0+ 개 플래그 문자열. 데이터 부족 시 빈 list.

    Guide:
        story 6 막 market analysis 박스 + AI 단기 경고/기회 답변. 플래그 ≥ 3 = 다중 신호 일치.

    When:
        Story flag 박스 + AI 단기 진단 답변.

    How:
        ``technicalVerdict`` 호출 → rsi/adx/bbPos/aboveSma20/aboveSma60/score 임계 비교.

    Requires:
        OHLCV ≥ 30 봉 + technicalVerdict 가용.

    Raises:
        없음.

    Example:
        >>> calcMarketAnalysisFlags(company)
        ['⚠ RSI 72 — 과매수 구간', '강한 추세 진행 중 (ADX 42)']

    See Also:
        - signal.analyzer.technicalVerdict : 입력 verdict
        - calcTechnicalSignals : recentEvents

    AIContext:
        "지금 종목 경고 사인" 답변 시 ⚠ 플래그 인용.
    """
    from dartlab.quant.signal.analyzer import technicalVerdict

    flags: list[str] = []

    ohlcv = _fetchOhlcv(company)
    if isEmptyDf(ohlcv) or len(ohlcv) < 30:
        return flags

    tv = technicalVerdict(
        ohlcv,
        stockCode=getattr(company, "stockCode", None),
        market=_detectMarket(company),
        benchmark=getattr(company, "benchmark", None),
        benchmarkMode=getattr(company, "benchmarkMode", "market"),
    )
    if not tv:
        return flags

    rsi = tv.get("rsi", 50)
    adx = tv.get("adx")
    bbPos = tv.get("bbPosition")
    score = tv.get("score", 0)

    # RSI 과매수/과매도
    if rsi >= 70:
        flags.append(f"⚠ RSI {rsi:.0f} — 과매수 구간 (70 이상)")
    elif rsi <= 30:
        flags.append(f"▲ RSI {rsi:.0f} — 과매도 구간 (30 이하), 반등 가능성")

    # ADX 추세 강도
    if adx is not None and adx >= 40:
        flags.append(f"강한 추세 진행 중 (ADX {adx:.0f})")

    # BB 위치
    if bbPos is not None:
        if bbPos >= 95:
            flags.append("⚠ 볼린저밴드 상단 돌파 — 과열 주의")
        elif bbPos <= 5:
            flags.append("볼린저밴드 하단 근접 — 반등 주시")

    # SMA 정배열/역배열
    above20 = tv.get("aboveSma20")
    above60 = tv.get("aboveSma60")
    if above20 and above60:
        flags.append("이동평균 정배열 (20일/60일 위) — 상승 추세 안정적")
    elif above20 is False and above60 is False:
        flags.append("⚠ 이동평균 역배열 (20일/60일 아래) — 하락 추세")

    # 종합 점수
    if score >= 3:
        flags.append("기술적 종합 강세 (score +3 이상)")
    elif score <= -3:
        flags.append("⚠ 기술적 종합 약세 (score -3 이하)")

    # 신호
    signals = tv.get("signals", {})
    gc = signals.get("goldenCross", 0)
    if gc > 0:
        flags.append("최근 골든크로스 발생 — 중기 상승 신호")
    elif gc < 0:
        flags.append("⚠ 최근 데드크로스 발생 — 중기 하락 신호")

    # 시장 리스크
    mr = calcMarketRisk(company)
    if mr:
        beta = mr.get("beta")
        if beta is not None and beta > 1.5:
            flags.append(f"⚠ 높은 베타 ({beta:.2f}) — 시장 급락 시 더 큰 손실 가능")
        atrPct = mr.get("atrPercent")
        if atrPct is not None and atrPct >= 5.0:
            flags.append(f"⚠ 일일 변동성 {atrPct:.1f}% — 고변동 종목")

    return flags

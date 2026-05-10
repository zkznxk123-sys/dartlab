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

# ── OHLCV 캐싱 헬퍼 ──


def _fetchOHLCV(company: Any) -> pl.DataFrame | None:
    """gather("price")로 OHLCV 수집 — Company._cache에 저장.

    모든 함수가 이 캐시를 공유하므로 네트워크 호출은 1회만 발생.
    """
    cache = getattr(company, "_cache", None)
    _KEY = "_quant_ohlcv"
    if cache is not None and _KEY in cache:
        return cache[_KEY]

    stockCode = getattr(company, "stockCode", None)
    if not stockCode:
        return None

    result = None
    try:
        from dartlab.gather.http import runAsync
        from dartlab.gather.price import fetch as fetchPrice

        snapshot = runAsync(fetchPrice(stockCode, market=_detectMarket(company)))
        if snapshot is not None and hasattr(snapshot, "ohlcv"):
            result = snapshot.ohlcv
        elif isinstance(snapshot, pl.DataFrame) and "close" in snapshot.columns:
            result = snapshot
    except (ImportError, AttributeError, ValueError, TypeError, RuntimeError):
        pass

    # fallback: GatherEntry 경유
    if result is None:
        try:
            from dartlab.gather.entry import GatherEntry

            raw = GatherEntry()("price", stockCode)
            if isinstance(raw, pl.DataFrame) and "close" in raw.columns:
                result = raw
        except (ImportError, ValueError, TypeError, RuntimeError):
            pass

    if cache is not None:
        cache[_KEY] = result
    return result


def _fetchBenchmarkForCompany(company: Any) -> pl.DataFrame | None:
    """시장 벤치마크 OHLCV — KRX 지수 SSOT."""
    cache = getattr(company, "_cache", None)
    stockCode = getattr(company, "stockCode", None)
    benchmark = getattr(company, "benchmark", None)
    benchmarkMode = getattr(company, "benchmarkMode", "market")
    cacheKey = f"_quant_benchmark:{benchmark or ''}:{benchmarkMode}"
    metaKey = f"{cacheKey}:meta"
    if cache is not None and cacheKey in cache:
        return cache[cacheKey]

    result = None
    meta = None
    try:
        from dartlab.quant.benchmark import fetchBenchmarkOhlcv

        result, meta = fetchBenchmarkOhlcv(
            stockCode,
            market=_detectMarket(company),
            benchmark=benchmark,
            benchmarkMode=benchmarkMode,
            returnMeta=True,
        )
    except (ImportError, ValueError, TypeError, RuntimeError):
        pass

    if cache is not None:
        cache[cacheKey] = result
        cache[metaKey] = meta
        cache["_quant_benchmark_meta"] = meta
    return result


def _benchmarkMetaForCompany(company: Any) -> dict | None:
    cache = getattr(company, "_cache", None)
    if cache is not None:
        return cache.get("_quant_benchmark_meta")
    return None


def _detectMarket(company: Any) -> str:
    """company.currency로 시장 감지."""
    return "US" if _isUSD(company) else "KR"


def _isUSD(company: Any) -> bool:
    return getattr(company, "currency", "KRW") == "USD"


# ── 독립 함수 (Company 또는 raw OHLCV 모두 지원) ──


@_memoized_calc
def calcTechnicalVerdict(company) -> dict | None:
    """기술적 종합 판단 — 강세/중립/약세 + 주요 지표.

    Args:
        company: Company 객체.

    Returns:
        dict — verdict, score, rsi, adx, aboveSma20, aboveSma60, bbPosition, signals.
    """
    ohlcv = _fetchOHLCV(company)
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

    Args:
        company: Company 객체 (gather("price")로 OHLCV 자동 수집).

    Returns:
        dict — signals, signalSummary, recentEvents.
    """
    ohlcv = _fetchOHLCV(company)
    if isEmptyDf(ohlcv) or len(ohlcv) < 60:
        return None

    close = ohlcv["close"].to_numpy().astype(np.float64)
    ohlcv["high"].to_numpy().astype(np.float64)
    ohlcv["low"].to_numpy().astype(np.float64)

    from dartlab.gather import indicators as ind
    from dartlab.quant import signals as sig

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

    Args:
        company: Company 객체.

    Returns:
        dict — value, r2, capmExpected, relativeStrength, interpretation.
    """
    ohlcv = _fetchOHLCV(company)
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

    Args:
        company: Company 객체.
        basePeriod: 기준 기간 (기본 최신).

    Returns:
        dict — financialGrade, technicalVerdict, divergence, diagnosis, matrix.
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
    ohlcv = _fetchOHLCV(company)
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

    Args:
        company: Company 객체.

    Returns:
        dict — beta, atr, atrPercent, relativeStrength, volatilityGrade, price.
    """
    ohlcv = _fetchOHLCV(company)
    if isEmptyDf(ohlcv) or len(ohlcv) < 30:
        return None

    close = ohlcv["close"].to_numpy().astype(np.float64)
    high = ohlcv["high"].to_numpy().astype(np.float64)
    low = ohlcv["low"].to_numpy().astype(np.float64)

    from dartlab.gather import indicators as ind

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

    Args:
        company: Company 객체.

    Returns:
        list[str] — 경고/기회 플래그 문자열 목록.
    """
    from dartlab.quant.signal.analyzer import technicalVerdict

    flags: list[str] = []

    ohlcv = _fetchOHLCV(company)
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


# ── Quant 서사 모듈 5개 (analysis calc 패턴 — 각각 독립, story 가 조합) ──


@_memoized_calc
def calcTrendData(company) -> dict | None:
    """추세 데이터 — MA 정배열 + ADX. 서사는 review가 생성.

    Parameters
    ----------
    company : Company
        분석 대상 기업.

    Returns
    -------
    dict
        data : dict | None — 추세 카테고리 상세
            label : str — 추세 방향 ("상승" | "횡보" | "하락")
            score : int — 추세 점수 (점)
        verdict : dict — calcTechnicalVerdict 전체 결과

    Examples
    --------
    >>> c.quant("trend")"""
    verdict = calcTechnicalVerdict(company)
    if verdict is None:
        return None
    return {"data": verdict.get("categories", {}).get("trend"), "verdict": verdict}


@_memoized_calc
def calcRiskData(company) -> dict | None:
    """리스크 데이터 — ATR + 베타 + 변동성. 서사는 review가 생성.

    Parameters
    ----------
    company : Company
        분석 대상 기업.

    Returns
    -------
    dict
        data : dict | None — calcMarketRisk 결과
            beta : float | None — 베타 계수 (배)
            atr : float | None — ATR 14일 (원)
            atrPercent : float | None — ATR / 종가 비율 (%)
            relativeStrength : float | None — 벤치마크 대비 상대강도 (배)
            volatilityGrade : str | None — "낮음" | "보통" | "높음" | "매우 높음"
            price : float — 최근 종가 (원)
        verdict : dict | None — calcTechnicalVerdict 전체 결과

    Examples
    --------
    >>> c.quant("risk")"""
    verdict = calcTechnicalVerdict(company)
    risk = calcMarketRisk(company)
    return {"data": risk, "verdict": verdict}


@_memoized_calc
def calcSignalData(company) -> dict | None:
    """수급 신호 데이터 — 최근 20일 매수/매도. 서사는 review가 생성.

    Parameters
    ----------
    company : Company
        분석 대상 기업.

    Returns
    -------
    dict
        data : dict | None — calcTechnicalSignals 결과
            signals : dict — 신호별 누적 점수
                goldenCross : int — 골든/데드크로스 누적
                rsiSignal : int — RSI 신호 누적
                macdSignal : int — MACD 신호 누적
                bollingerSignal : int — 볼린저 신호 누적
            signalSummary : dict
                bullish : int — 매수 신호 건수 (건)
                bearish : int — 매도 신호 건수 (건)
            recentEvents : list[dict] — 최근 이벤트 목록

    Examples
    --------
    >>> c.quant("signal")"""
    signals = calcTechnicalSignals(company)
    return {"data": signals}


@_memoized_calc
def calcStrategyData(company) -> dict | None:
    """전략 검증 데이터 — 스타일별 Sharpe + 진입. 서사는 review가 생성.

    Parameters
    ----------
    company : Company
        분석 대상 기업.

    Returns
    -------
    dict
        data : dict | None — calcStrategySnapshot 결과
            {style_key} : dict — 스타일별 백테스트 결과
                sharpe : float — Sharpe 비율 (배)
                mdd : float — 최대 낙폭 (%)
                dsr : float — Deflated Sharpe Ratio (배)
                trades : int — 거래 횟수 (건)
                entry_today : bool — 오늘 진입 신호 여부
                exit_today : bool — 오늘 청산 신호 여부
                stop_level : float | None — 스톱 가격 (원)
                status : str — "ok" | "error" | "not_applicable"

    Examples
    --------
    >>> c.quant("strategy")"""
    strategy = calcStrategySnapshot(company)
    return {"data": strategy}


@_memoized_calc
def calcCrosscheckData(company) -> dict | None:
    """교차 검증 데이터 — analysis 등급 vs 기술적 판단. 서사는 review가 생성.

    Parameters
    ----------
    company : Company
        분석 대상 기업.

    Returns
    -------
    dict
        data : dict | None — calcFundamentalDivergence 결과
            financialGrade : str | None — 재무 등급 ("A+" ~ "D")
            technicalVerdict : str | None — "강세" | "중립" | "약세"
            technicalScore : int — 기술적 점수 (점)
            divergence : str — 괴리 유형 ("순풍" | "괴리" | "위험" 등)
            diagnosis : str — 진단 메시지
            matrix : str — 2×3 매트릭스 키

    Examples
    --------
    >>> c.quant("crosscheck")"""
    divergence = calcFundamentalDivergence(company)
    return {"data": divergence}


@_memoized_calc
def calcQuantConclusionData(company) -> dict | None:
    """결론 데이터 — 5축 방향 집계. 서사는 review가 생성.

    Parameters
    ----------
    company : Company
        분석 대상 기업.

    Returns
    -------
    dict
        trend_label : str — 추세 방향 라벨 ("상승" | "횡보" | "하락")
        bullish : int — 매수 신호 건수 (건)
        bearish : int — 매도 신호 건수 (건)
        active_styles : list[str] — 오늘 진입 신호가 활성인 스타일명
        diagnosis : str — 교차검증 진단 메시지

    Examples
    --------
    >>> c.quant("conclusion")"""
    verdict = calcTechnicalVerdict(company)
    signals = calcTechnicalSignals(company)
    strategy = calcStrategySnapshot(company)
    divergence = calcFundamentalDivergence(company)

    if verdict is None:
        return None

    cats = verdict.get("categories", {})
    trendLabel = cats.get("trend", {}).get("label", "")
    summary = (signals or {}).get("signalSummary", {})
    bullish = summary.get("bullish", 0)
    bearish = summary.get("bearish", 0)
    activeStyles = []
    if strategy:
        for k, v in strategy.items():
            if isinstance(v, dict) and v.get("entry_today") and v.get("status") == "ok":
                activeStyles.append(k)
    diagnosis = (divergence or {}).get("diagnosis", "")
    return {
        "trend_label": trendLabel,
        "bullish": bullish,
        "bearish": bearish,
        "active_styles": activeStyles,
        "diagnosis": diagnosis,
    }


@_memoized_calc
def calcStrategySnapshot(company) -> dict | None:
    """전략별 진입 진단 — 8 검증된 스타일 일괄 백테스트.

    Strategy DSL 의 story 6막 (전망) 통합 진입점. 시총 의존 0.

    Args:
        company: Company 객체.

    Returns:
        dict {style_key: {sharpe, mdd, dsr, trades, entry_today, exit_today, status}}
        또는 None (데이터 부족).
    """
    ohlcv = _fetchOHLCV(company)
    if isEmptyDf(ohlcv) or len(ohlcv) < 60:
        return None

    from dartlab.quant._ax_strategy import runEntry, runStyle
    from dartlab.quant.strategy.presets import STYLE_REGISTRY

    code = getattr(company, "stockCode", None) or getattr(company, "stock_code", None)
    if not code:
        return None

    # 1) 백테스트 (8 스타일) — 5년 OHLCV 로 학술 결과 재현 (Phase 4 R5)
    bt_results = runStyle(code, name="all", start="2014-01-01")
    # 2) 진입 진단 (현재 시점)
    entry_results = runEntry(code, style="all", start="2014-01-01")

    snap: dict = {}
    for key in STYLE_REGISTRY().keys():
        bt = bt_results.get(key)
        ev = entry_results.get(key)
        if bt is None:
            continue
        snap[key] = {
            "sharpe": float(bt.sharpe),
            "mdd": float(bt.mdd),
            "dsr": float(bt.dsr),
            "trades": int(bt.trades.height) if bt.trades is not None else 0,
            "entry_today": bool(ev.active) if ev else False,
            "exit_today": bool(ev.exit_today) if ev else False,
            "stop_level": float(ev.stop_level) if ev and ev.stop_level else None,
            "status": bt.status,
            "reason": bt.reason,
        }
    return snap


def calcActionableTargets(company, *, overrides: dict | None = None) -> dict | None:
    """기술적 관점의 구체적 행동 목표 — 진입/청산 가격. overrides로 AI 조율 가능.

    현재 가격, 기술적 판정, 지지/저항선, 신호별 트리거 가격을 반환.

    Returns
    -------
    dict | None
        currentPrice : float
        technicalVerdict : str
        support : float | None — 지지선
        resistance : float | None — 저항선
        targets : list[dict]
            signal : str — 신호 이름
            triggerPrice : float — 트리거 가격
            action : str — 행동 제안
            confidence : str — low/medium/high
    """
    try:
        ohlcv = _fetchOHLCV(company)
    except (AttributeError, ValueError, TypeError):
        return None

    if isEmptyDf(ohlcv):
        return None

    closes = ohlcv["close"].to_list()
    if not closes or len(closes) < 20:
        return None

    current = closes[-1]

    # 지지/저항: 20일 최저/최고
    low20 = min(closes[-20:])
    high20 = max(closes[-20:])

    # 볼린저 밴드 (20일)
    import numpy as np

    arr = np.array(closes[-20:], dtype=float)
    ma20 = float(np.mean(arr))
    std20 = float(np.std(arr))
    bb_lower = ma20 - 2 * std20
    bb_upper = ma20 + 2 * std20

    targets = []

    # 볼린저 하단 접근
    if current > bb_lower:
        targets.append(
            {
                "signal": "볼린저 하단 접근",
                "triggerPrice": round(bb_lower),
                "action": "분할 매수 검토",
                "confidence": "medium",
            }
        )

    # RSI 과매도 (간략 계산)
    if len(closes) >= 14:
        gains = [max(0, closes[i] - closes[i - 1]) for i in range(-14, 0)]
        losses = [max(0, closes[i - 1] - closes[i]) for i in range(-14, 0)]
        avg_gain = sum(gains) / 14
        avg_loss = sum(losses) / 14
        rsi = 100 - 100 / (1 + avg_gain / avg_loss) if avg_loss > 0 else 100

        if rsi > 30:
            # RSI가 30 이하가 될 가격 역산 (근사)
            rsi_target = round(current * 0.90)  # 약 10% 하락 시 과매도 근접
            targets.append(
                {
                    "signal": "RSI 과매도 접근",
                    "triggerPrice": rsi_target,
                    "action": "적극 매수 검토",
                    "confidence": "high" if rsi < 40 else "medium",
                }
            )

    verdict = calcTechnicalVerdict(company)
    tech_label = verdict.get("verdict", "중립") if verdict else "중립"

    return {
        "currentPrice": round(current),
        "technicalVerdict": tech_label,
        "support": round(low20),
        "resistance": round(high20),
        "bollingerLower": round(bb_lower),
        "bollingerUpper": round(bb_upper),
        "targets": targets,
    }

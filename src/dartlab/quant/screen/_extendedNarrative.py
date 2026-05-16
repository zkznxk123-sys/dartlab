"""quant/screen/extended 서사 + 전략 8 함수 분리.

quant/screen/extended.py 의 story 6막 서사 소비 함수들을 분리.
identity 보존을 위해 extended.py 가 본 모듈에서 re-export 한다.

함수 (analysis calc 패턴):
- calcTrendData — 추세 카테고리 + verdict
- calcRiskData — ATR + 베타 + 변동성
- calcSignalData — 최근 20일 매수/매도 신호
- calcStrategyData — 스타일별 Sharpe + 진입
- calcCrosscheckData — analysis 등급 vs 기술적 판단
- calcQuantConclusionData — 5축 방향 집계
- calcStrategySnapshot — 8 스타일 백테스트 + 진입 진단
- calcActionableTargets — 진입/청산 가격 목표
"""

from __future__ import annotations

import numpy as np

from dartlab.core.memory import memoizedCalc as _memoized_calc
from dartlab.core.polarsUtil import isEmptyDf
from dartlab.quant.screen._extendedCache import _fetchOhlcv


def _calls():
    """Lazy import — 순환 회피."""
    from dartlab.quant.screen.extended import (
        calcFundamentalDivergence,
        calcMarketRisk,
        calcTechnicalSignals,
        calcTechnicalVerdict,
    )

    return calcTechnicalVerdict, calcTechnicalSignals, calcMarketRisk, calcFundamentalDivergence


@_memoized_calc
def calcTrendData(company) -> dict | None:
    """추세 데이터 — MA 정배열 + ADX. 서사는 review가 생성."""
    calcTechnicalVerdict, *_ = _calls()
    verdict = calcTechnicalVerdict(company)
    if verdict is None:
        return None
    return {"data": verdict.get("categories", {}).get("trend"), "verdict": verdict}


@_memoized_calc
def calcRiskData(company) -> dict | None:
    """리스크 데이터 — ATR + 베타 + 변동성."""
    calcTechnicalVerdict, _, calcMarketRisk, _ = _calls()
    verdict = calcTechnicalVerdict(company)
    risk = calcMarketRisk(company)
    return {"data": risk, "verdict": verdict}


@_memoized_calc
def calcSignalData(company) -> dict | None:
    """수급 신호 데이터 — 최근 20일 매수/매도."""
    _, calcTechnicalSignals, *_ = _calls()
    signals = calcTechnicalSignals(company)
    return {"data": signals}


@_memoized_calc
def calcStrategyData(company) -> dict | None:
    """전략 검증 데이터 — 스타일별 Sharpe + 진입.

    Example:
        >>> calcStrategyData(company)

    Requires:
        company 가 stockCode 보유 + OHLCV fetch 가능.

    Raises:
        없음 (실패는 None).
    """
    strategy = calcStrategySnapshot(company)
    return {"data": strategy}


@_memoized_calc
def calcCrosscheckData(company) -> dict | None:
    """교차 검증 데이터 — analysis 등급 vs 기술적 판단."""
    _, _, _, calcFundamentalDivergence = _calls()
    divergence = calcFundamentalDivergence(company)
    return {"data": divergence}


@_memoized_calc
def calcQuantConclusionData(company) -> dict | None:
    """결론 데이터 — 5축 방향 집계."""
    calcTechnicalVerdict, calcTechnicalSignals, _, calcFundamentalDivergence = _calls()
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
    """
    ohlcv = _fetchOhlcv(company)
    if isEmptyDf(ohlcv) or len(ohlcv) < 60:
        return None

    from dartlab.quant.screen.axStrategy import runEntry, runStyle
    from dartlab.quant.strategy.presets import STYLE_REGISTRY

    code = getattr(company, "stockCode", None) or getattr(company, "stock_code", None)
    if not code:
        return None

    bt_results = runStyle(code, name="all", start="2014-01-01")
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
    """기술적 관점의 구체적 행동 목표 — 진입/청산 가격."""
    try:
        ohlcv = _fetchOhlcv(company)
    except (AttributeError, ValueError, TypeError):
        return None

    if isEmptyDf(ohlcv):
        return None

    closes = ohlcv["close"].to_list()
    if not closes or len(closes) < 20:
        return None

    current = closes[-1]

    low20 = min(closes[-20:])
    high20 = max(closes[-20:])

    arr = np.array(closes[-20:], dtype=float)
    ma20 = float(np.mean(arr))
    std20 = float(np.std(arr))
    bb_lower = ma20 - 2 * std20
    bb_upper = ma20 + 2 * std20

    targets = []

    if current > bb_lower:
        targets.append(
            {
                "signal": "볼린저 하단 접근",
                "triggerPrice": round(bb_lower),
                "action": "분할 매수 검토",
                "confidence": "medium",
            }
        )

    if len(closes) >= 14:
        gains = [max(0, closes[i] - closes[i - 1]) for i in range(-14, 0)]
        losses = [max(0, closes[i - 1] - closes[i]) for i in range(-14, 0)]
        avg_gain = sum(gains) / 14
        avg_loss = sum(losses) / 14
        rsi = 100 - 100 / (1 + avg_gain / avg_loss) if avg_loss > 0 else 100

        if rsi > 30:
            rsi_target = round(current * 0.90)
            targets.append(
                {
                    "signal": "RSI 과매도 접근",
                    "triggerPrice": rsi_target,
                    "action": "적극 매수 검토",
                    "confidence": "high" if rsi < 40 else "medium",
                }
            )

    calcTechnicalVerdict, *_ = _calls()
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


__all__ = [
    "calcActionableTargets",
    "calcCrosscheckData",
    "calcQuantConclusionData",
    "calcRiskData",
    "calcSignalData",
    "calcStrategyData",
    "calcStrategySnapshot",
    "calcTrendData",
]

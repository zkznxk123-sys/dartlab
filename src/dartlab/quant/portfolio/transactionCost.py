"""Almgren-Chriss Transaction Cost 모델 — Almgren & Chriss (2000).

학술: "Optimal execution of portfolio transactions" — Risk minimization vs cost.

전체 비용 분해 :
    Spread cost (커미션 + 호가차)
    Permanent impact (시장 가격 영구 변동) : γ · X / V
    Temporary impact (실행 중 일시 가격 변동) : η · (X / τ) / V

X = 거래량 (주식 수)
V = 일평균 거래량
τ = 실행 시간 (일)
γ = permanent impact 계수 (default 2.5e-7 / V)
η = temporary impact 계수 (default 1e-6 / V)

Sharpe net of cost = (raw return - TC) / vol
"""

from __future__ import annotations

import numpy as np


def almgrenChrissCost(
    *,
    quantity: float,
    avgDailyVolume: float,
    price: float,
    duration: float = 1.0,
    spreadBp: float = 5.0,
    permImpactCoef: float = 2.5e-7,
    tempImpactCoef: float = 1e-6,
    volatility: float = 0.20,
) -> dict:
    """Almgren-Chriss 단일 거래의 비용 분해.

    Capabilities:
        - Spread + Permanent + Temporary impact 3종 분해
        - 총 비용 (원) + bp 환산
        - Risk-cost trade-off (variance term)

    AIContext:
        - Sprint 3 backtest 현실성 — strategy/backtest 의 sharpeNetOfCost 의 ground truth
        - 한국 시장 캘리브레이션: 5bp 스프레드 (KOSPI200), 10bp (KOSDAQ)

    Args:
        quantity: 거래 수량 (주).
        avgDailyVolume: 일평균 거래량 (주).
        price: 평균 가격 (원).
        duration: 실행 시간 (일). 기본 ``1.0``.
        spreadBp: 호가 스프레드 (bp). 기본 ``5.0`` (KOSPI200 평균).
        permImpactCoef: γ. 기본 ``2.5e-7``.
        tempImpactCoef: η. 기본 ``1e-6``.
        volatility: 일변동성 (annualized %). 기본 ``0.20``.

    Returns:
        dict
            spreadCost : float — 원
            permanentImpact : float — 원
            temporaryImpact : float — 원
            riskCost : float — Bertsimas-Lo variance term (원)
            totalCost : float — 합 (원)
            costBp : float — 거래대금 대비 bp
            participationRate : float — X / V
            interpretation : str

    Guide:
        Almgren-Chriss (2001) — 단일 거래 비용 분해 표준. participationRate
        (X/V) > 0.05 = 큰 영향, > 0.10 = 위험.

    When:
        Quant 백테스트 현실성 + AI 거래 비용 답변.

    How:
        spread (bp 변환) + permanent (γ × X) + temporary (η × X / 거래시간) +
        risk (σ²X²T) → bp 환산.

    Requires:
        quantity/ADV/price 양수.

    Raises:
        없음 — invalid 시 error 키.

    Example:
        >>> r = almgrenChrissCost(quantity=10000, avgDailyVolume=500000, price=70000)
        >>> r["participationRate"]
        0.02

    See Also:
        - vectorBacktest : feeBps/slipBps/impactBpsPerPct 파라미터로 사용
    """
    if avgDailyVolume <= 0 or price <= 0 or quantity <= 0:
        return {"error": "invalid input"}

    notional = quantity * price
    p_rate = quantity / avgDailyVolume

    spread_cost = notional * spreadBp / 10000
    perm = permImpactCoef * (quantity**2) * price / avgDailyVolume
    temp = tempImpactCoef * (quantity**2) * price / (avgDailyVolume * max(duration, 1e-9))

    # Bertsimas-Lo variance term (risk-aversion proxy)
    sigma_daily = volatility / np.sqrt(252)
    risk = (sigma_daily * price) ** 2 * quantity**2 * duration / 3

    total = spread_cost + perm + temp
    cost_bp = (total / notional) * 10000

    return {
        "spreadCost": round(spread_cost, 2),
        "permanentImpact": round(perm, 2),
        "temporaryImpact": round(temp, 2),
        "riskCost": round(risk, 2),
        "totalCost": round(total, 2),
        "costBp": round(cost_bp, 2),
        "participationRate": round(p_rate, 4),
        "notional": round(notional, 0),
        "interpretation": (
            f"거래 {round(quantity, 0):.0f}주 × {round(price, 0):.0f}원 = {notional / 1e6:.1f}M원, "
            f"비용 {round(total, 0):.0f}원 ({round(cost_bp, 1)}bp), "
            f"참여율 {round(p_rate * 100, 2)}%."
        ),
    }


def sharpeNetOfCost(
    rawReturns: np.ndarray,
    *,
    avgTradeSize: float = 0.01,
    avgVolume: float = 1e6,
    spreadBp: float = 5.0,
    turnoverPerYear: float = 5.0,
) -> dict:
    """전략의 Sharpe net of Almgren-Chriss cost.

    Args:
        rawReturns: 일별 수익률 (소수, 1차원).
        avgTradeSize: 평균 거래 단위 (포트폴리오 비중, 0~1). 기본 ``0.01`` (=1%).
        avgVolume: 평균 거래량 가정.
        spreadBp: 스프레드 bp. 기본 ``5``.
        turnoverPerYear: 연간 turnover 회전률. 기본 ``5.0``.

    Returns:
        dict
            grossSharpe : float — 비용 전 Sharpe
            costPerTradeBp : float — 거래당 비용 (bp)
            annualCost : float — 연간 총 비용 (%)
            netSharpe : float — Sharpe (cost 차감 후)
            costShare : float — 비용이 gross 수익 대비 차지 비율 (%)
            interpretation : str
    """
    r = np.asarray(rawReturns, dtype=np.float64)
    r = r[np.isfinite(r)]
    if len(r) < 30:
        return {"error": "too few returns"}

    gross_mean = float(r.mean()) * 252
    gross_std = float(r.std(ddof=1)) * np.sqrt(252)
    gross_sharpe = gross_mean / gross_std if gross_std > 0 else 0.0

    # 거래당 비용 = spread + impact (단순화)
    p_rate = avgTradeSize  # 단위 weight = 참여율 proxy
    impact_bp = 100 * 2.5e-7 * (p_rate * avgVolume) ** 2 / avgVolume / 10000
    cost_per_trade_bp = spreadBp + impact_bp
    annual_cost_pct = cost_per_trade_bp * turnoverPerYear / 10000  # 십진수

    net_mean = gross_mean - annual_cost_pct
    net_sharpe = net_mean / gross_std if gross_std > 0 else 0.0
    cost_share = (annual_cost_pct / gross_mean * 100) if gross_mean > 0 else 0.0

    return {
        "grossSharpe": round(gross_sharpe, 3),
        "costPerTradeBp": round(cost_per_trade_bp, 2),
        "annualCost": round(annual_cost_pct * 100, 2),
        "netSharpe": round(net_sharpe, 3),
        "costShare": round(cost_share, 1),
        "interpretation": (
            f"gross Sharpe {round(gross_sharpe, 2)} → net {round(net_sharpe, 2)} "
            f"(연 비용 {round(annual_cost_pct * 100, 2)}%, gross 의 {round(cost_share, 0)}% 차감)."
        ),
    }

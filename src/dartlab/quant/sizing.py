"""포지션 사이징 + 레버리지 결정 — 순수 numpy.

학술 근거:
- Kelly (1956): A New Interpretation of Information Rate
- Maillard, Roncalli, Teiletche (2010): Risk Parity / 역변동성
- Carver (2015): Systematic Trading — Volatility Targeting
- Roncalli (2013): Introduction to Risk Parity and Budgeting

dartlab.quant("켈리", ...) 같은 직접 축으로 노출하지 않고 헬퍼 함수만 제공.
factor/portfolio 엔진과 story/AI에서 import해서 사용.
"""

from __future__ import annotations

import numpy as np


def kellyFraction(winProb: float, winLossRatio: float, *, fraction: float = 1.0) -> float:
    """Kelly criterion — 베팅 비율.

    f* = (p × b - (1-p)) / b
    where p = win probability, b = win/loss ratio (avg win / avg loss).

    Args:
        win_prob: 0~1 승률
        win_loss_ratio: 평균이익/평균손실 비율 (양수)
        fraction: 0~1 사이 fractional Kelly (기본 full=1.0).
                  실무는 보통 half-Kelly(0.5) 또는 quarter(0.25).

    Returns:
        포지션 비율 (0~1, 음수면 베팅 안 함).
    """
    if winProb <= 0 or winProb >= 1 or winLossRatio <= 0:
        return 0.0
    full = (winProb * winLossRatio - (1 - winProb)) / winLossRatio
    return float(max(0.0, min(1.0, full * fraction)))


def kellyContinuous(meanReturn: float, variance: float) -> float:
    """연속 Kelly — μ/σ² (정규분포 가정).

    Thorp (2006), MacLean & Ziemba 등. log-utility maximizer.

    Args:
        mean_return: 기대수익률
        variance: 분산

    Returns:
        Kelly 비율 (0이상). σ²=0이면 0.
    """
    if variance <= 0:
        return 0.0
    return float(max(0.0, meanReturn / variance))


def inverseVolatilityWeights(volatilities: np.ndarray) -> np.ndarray:
    """역변동성 가중 — w_i ∝ 1/σ_i, 합=1.

    Maillard 2010 IVP. 가장 단순한 risk parity 베이스라인.
    """
    vols = np.asarray(volatilities, dtype=float)
    inv = 1 / np.where(vols > 0, vols, np.inf)
    s = inv.sum()
    if s == 0:
        return np.zeros_like(vols)
    return inv / s


def volatilityTargetLeverage(
    realizedVol: float,
    targetVol: float = 0.10,
    maxLeverage: float = 3.0,
) -> float:
    """변동성 타겟팅 레버리지 — target_vol / realized_vol.

    Carver 2015. 자산의 실현 변동성이 목표보다 낮으면 leverage up,
    높으면 down. 책 10장 핵심 룰.

    Args:
        realized_vol: 실현 (보통 연환산) 변동성
        target_vol: 목표 (기본 10%)
        max_leverage: 상한 (기본 3배)

    Returns:
        포지션 사이즈 곱수 (0 ~ max_leverage)
    """
    if realizedVol <= 0:
        return 0.0
    lev = targetVol / realizedVol
    return float(max(0.0, min(maxLeverage, lev)))


def sharpeBasedSize(sharpe: float, targetSharpe: float = 1.0, *, cap: float = 1.0) -> float:
    """샤프비율 기반 단순 사이징 — sharpe / target_sharpe로 비율 결정.

    sharpe ≥ target → cap, 음수 → 0.
    """
    if sharpe <= 0:
        return 0.0
    return float(min(cap, sharpe / max(targetSharpe, 1e-12) * cap))


def riskBudgetLeverage(
    portfolioVol: float,
    riskBudget: float,
    maxLeverage: float = 2.0,
) -> float:
    """리스크 버짓 레버리지 — 포트폴리오 변동성을 risk_budget에 맞춤.

    책 10장: 자본의 % 단위로 risk_budget을 정하고 그 한도 안에서 portfolio leverage 결정.
    """
    if portfolioVol <= 0:
        return 0.0
    return float(max(0.0, min(maxLeverage, riskBudget / portfolioVol)))


# 0.10 BC 깸 — snake_case alias 제거.

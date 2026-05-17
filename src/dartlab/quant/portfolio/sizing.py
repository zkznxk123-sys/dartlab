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
        winProb: 0~1 승률.
        winLossRatio: 평균이익/평균손실 비율 (양수).
        fraction: 0~1 사이 fractional Kelly. 기본 ``1.0`` full. 실무는 보통 half-Kelly(0.5) 또는 quarter(0.25).

    Returns:
        float — 포지션 비율 (0~1). 음수면 0.

    Capabilities:
        - Kelly 공식 정확 + fractional Kelly 보정 + 0~1 클립
        - winProb 경계 (0/1) 또는 winLossRatio 비양수 시 안전 0

    Guide:
        Kelly (1956) full = optimal log-utility. 실무는 절반·1/4 Kelly 보수적 사용 (반감기 효과).

    When:
        Position 사이징 + AI 베팅 비율 답변.

    How:
        full = (p*b - (1-p)) / b → fraction 곱 → 0~1 클립.

    Requires:
        winProb ∈ (0,1) + winLossRatio > 0.

    Raises:
        없음 — 비유효 시 0.

    Example:
        >>> kellyFraction(0.55, 1.5, fraction=0.5)
        0.122

    See Also:
        - kellyContinuous : μ/σ² 연속형
        - volatilityTargetLeverage : 변동성 타겟

    AIContext:
        "Kelly 비율 얼마" 답변 시 fraction × full 인용.
    """
    if winProb <= 0 or winProb >= 1 or winLossRatio <= 0:
        return 0.0
    full = (winProb * winLossRatio - (1 - winProb)) / winLossRatio
    return float(max(0.0, min(1.0, full * fraction)))


def kellyContinuous(meanReturn: float, variance: float) -> float:
    """연속 Kelly — μ/σ² (정규분포 가정).

    Thorp (2006), MacLean & Ziemba 등. log-utility maximizer.

    Args:
        meanReturn: 기대수익률
        variance: 분산

    Returns:
        Kelly 비율 (0이상). σ²=0이면 0.

    Example:
        >>> kellyContinuous(0.10, 0.04)
        2.5

    Requires:
        meanReturn 연환산 + variance 연환산 일치.

    Raises:
        없음.
    """
    if variance <= 0:
        return 0.0
    return float(max(0.0, meanReturn / variance))


def inverseVolatilityWeights(volatilities: np.ndarray) -> np.ndarray:
    """역변동성 가중 — w_i ∝ 1/σ_i, 합=1.

    Maillard 2010 IVP. 가장 단순한 risk parity 베이스라인.

    Capabilities:
        - 변동성 ↑ → 가중 ↓ 역수 비례 + 합 1 정규화
        - σ ≤ 0 인 자산은 무한대 → 가중 0 효과

    Args:
        volatilities: 자산별 변동성 array.

    Returns:
        np.ndarray — 0~1 가중치, 합 1.

    Guide:
        ERC (allocateERC) 보다 단순. 상관 무시하므로 자산 수 늘수록 ERC 와 차이.

    When:
        Portfolio risk parity 베이스라인 + AI 변동성 균등 답변.

    How:
        ``1/σ`` → 합으로 정규화.

    Requires:
        volatilities array (양수 권장).

    Raises:
        없음 — 합 0 시 zeros 반환.

    Example:
        >>> inverseVolatilityWeights(np.array([0.1, 0.2, 0.4]))
        array([0.5714, 0.2857, 0.1428])

    See Also:
        - allocateERC : 상관 고려 ERC
        - volatilityTargetLeverage : 단일 자산 사이징

    AIContext:
        "역변동성 가중" 답변 시 weights array 인용.
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
        realizedVol: 실현 (보통 연환산) 변동성.
        targetVol: 목표 변동성. 기본 ``0.10`` (10%).
        maxLeverage: 레버리지 상한. 기본 ``3.0``.

    Returns:
        float — 포지션 사이즈 곱수 (0 ~ maxLeverage).

    Capabilities:
        - 실현 변동성 < 목표 → leverage up (자본 효율) , 높으면 down (위험 절감)
        - maxLeverage 상한 + 음수 클립

    Guide:
        Carver 2015 Systematic Trading Ch.10. targetVol 10% 표준 (개인 보수적), 기관은 15~20%.

    When:
        포지션 동적 사이징 + AI "지금 사이즈 얼마" 답변.

    How:
        ``lev = targetVol / realizedVol`` → clip(0, maxLeverage).

    Requires:
        realizedVol > 0 + 동일 시간 단위 (annualized 권장).

    Raises:
        없음 — realizedVol ≤ 0 시 0.

    Example:
        >>> volatilityTargetLeverage(0.05, 0.10)
        2.0

    See Also:
        - kellyFraction : 승률 기반
        - riskBudgetLeverage : 리스크 버짓

    AIContext:
        "변동성 타겟 레버리지" 답변 시 lev + 상한 인용.
    """
    if realizedVol <= 0:
        return 0.0
    lev = targetVol / realizedVol
    return float(max(0.0, min(maxLeverage, lev)))


def sharpeBasedSize(sharpe: float, targetSharpe: float = 1.0, *, cap: float = 1.0) -> float:
    """샤프비율 기반 단순 사이징 — sharpe / target_sharpe로 비율 결정.

    sharpe ≥ target → cap, 음수 → 0.

    Example:
        >>> sharpeBasedSize(0.8, 1.0)
        0.8

    Requires:
        sharpe 연환산 + targetSharpe > 0.

    Raises:
        없음.
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

    Example:
        >>> riskBudgetLeverage(0.15, 0.10)
        0.667

    Requires:
        portfolioVol 연환산 + riskBudget 동일 단위.

    Raises:
        없음.
    """
    if portfolioVol <= 0:
        return 0.0
    return float(max(0.0, min(maxLeverage, riskBudget / portfolioVol)))


# 0.10 BC 깸 — snake_case alias 제거.

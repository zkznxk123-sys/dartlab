"""Growth-at-Risk — Adrian, Boyarchenko, Giannone (2019) AER.

FCI → GDP 성장률의 조건부 분위를 추정.
평균 GDP가 아니라 worst-case(5th percentile)가 금융 긴축기에 급락.
IMF 공식 도구, 20+ 중앙은행 사용.

분위회귀: IRLS(Iteratively Reweighted Least Squares)로 numpy만 구현.
pinball loss 최소화 — scipy.optimize 불필요.
"""

from __future__ import annotations

import numpy as np


def _quantileRegression(
    X: np.ndarray,
    y: np.ndarray,
    tau: float,
    maxIter: int = 50,
    tol: float = 1e-6,
) -> np.ndarray:
    """분위회귀 — IRLS 방식.

    min Σ ρ_τ(y - Xβ), ρ_τ(u) = u(τ - I(u<0))

    Args:
        X: (n, p) 디자인 행렬 (상수항 포함)
        y: (n,) 종속변수
        tau: 분위수 (0.05, 0.25, 0.50, 0.75, 0.95)
        max_iter: 최대 반복
        tol: 수렴 임계값

    Returns:
        β: (p,) 회귀계수
    """
    n = len(y)
    # OLS 초기값
    beta = np.linalg.lstsq(X, y, rcond=None)[0]

    for _ in range(maxIter):
        residuals = y - X @ beta
        # IRLS 가중치: pinball loss의 미분
        weights = np.where(residuals >= 0, tau, 1 - tau)
        # 0 근처 안정화
        weights = np.maximum(weights, 1e-8)

        W = np.diag(weights)
        # 가중 최소제곱: (X'WX)^{-1} X'Wy
        XtWX = X.T @ W @ X
        XtWy = X.T @ W @ y
        try:
            beta_new = np.linalg.solve(XtWX, XtWy)
        except np.linalg.LinAlgError:
            break

        if np.max(np.abs(beta_new - beta)) < tol:
            beta = beta_new
            break
        beta = beta_new

    return beta


def growthAtRisk(
    fciValues: list[float],
    gdpGrowthValues: list[float],
    *,
    horizon: int = 4,
    quantiles: tuple[float, ...] = (0.05, 0.25, 0.50, 0.75, 0.95),
) -> dict | None:
    """FCI → GDP 성장률 조건부 분위 추정.

    Args:
        fci_values: FCI 시계열 (분기 또는 월간, 시간 순서)
        gdp_growth_values: GDP 성장률 시계열 (%, 동일 주파수)
        horizon: 예측 분기 수 (기본 4 = 1년 후)
        quantiles: 추정할 분위수

    Returns:
        dict with GaR percentiles, tail risk, skewness
        None if insufficient data
    """
    fci = np.array(fciValues, dtype=np.float64)
    gdp = np.array(gdpGrowthValues, dtype=np.float64)

    # 동일 길이로 맞춤
    min_len = min(len(fci), len(gdp))
    if min_len < 20:  # 최소 20 관측치
        return None

    fci = fci[:min_len]
    gdp = gdp[:min_len]

    # NaN 제거
    mask = ~(np.isnan(fci) | np.isnan(gdp))
    fci = fci[mask]
    gdp = gdp[mask]

    if len(fci) < 20:
        return None

    # horizon 만큼 shift: FCI(t) → GDP(t+h)
    if horizon > 0 and len(fci) > horizon:
        X_raw = fci[:-horizon]
        y = gdp[horizon:]
    else:
        X_raw = fci
        y = gdp

    if len(X_raw) < 15:
        return None

    # 디자인 행렬 (상수항 + FCI)
    n = len(X_raw)
    X = np.column_stack([np.ones(n), X_raw])

    # 각 분위에서 회귀
    results: dict[float, float] = {}
    current_fci = float(fci[-1])
    x_pred = np.array([1.0, current_fci])

    for tau in quantiles:
        beta = _quantileRegression(X, y, tau)
        predicted = float(x_pred @ beta)
        results[tau] = round(predicted, 2)

    # 꼬리 리스크 판정
    gar5 = results.get(0.05, 0.0)
    median = results.get(0.50, 0.0)

    if gar5 < -2.0:
        tail_risk, tail_label = "high", "높음"
    elif gar5 < -0.5:
        tail_risk, tail_label = "elevated", "주의"
    elif gar5 < 0.5:
        tail_risk, tail_label = "moderate", "보통"
    else:
        tail_risk, tail_label = "low", "낮음"

    # 비대칭도: (95th - median) - (median - 5th)
    gar95 = results.get(0.95, 0.0)
    skewness = round((gar95 - median) - (median - gar5), 2)

    desc_parts = [f"GaR 5th={gar5:+.1f}%"]
    if tail_risk in ("high", "elevated"):
        desc_parts.append(f"하방 꼬리 리스크 {tail_label}")
    desc_parts.append(f"중위 {median:+.1f}%")

    return {
        "currentGaR5": gar5,
        "currentGaR25": results.get(0.25, 0.0),
        "median": median,
        "currentGaR75": results.get(0.75, 0.0),
        "currentGaR95": gar95,
        "currentFCI": round(current_fci, 3),
        "tailRisk": tail_risk,
        "tailRiskLabel": tail_label,
        "skewness": skewness,
        "horizon": horizon,
        "observations": n,
        "description": ". ".join(desc_parts) + ".",
    }

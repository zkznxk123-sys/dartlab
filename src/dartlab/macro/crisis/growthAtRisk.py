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

    Capabilities:
        Adrian-Boyarchenko-Giannone (2019 AER) Growth-at-Risk — FCI 를 조건으로
        h 분기 후 GDP 성장률 분위 회귀 (5/25/50/75/95) → 하방 꼬리 리스크
        (GaR 5th) + 비대칭도 (skewness). IMF 표준 매크로 리스크 지표.

    Args:
        fciValues: FCI 시계열 (분기 또는 월간, ≥ 20 관측치).
        gdpGrowthValues: GDP 성장률 (%) 시계열 (동일 주파수).
        horizon: 예측 분기 수. 기본 4 (1 년).
        quantiles: 추정 분위 tuple. 기본 (0.05, 0.25, 0.50, 0.75, 0.95).

    Returns:
        dict — currentGaR5/currentGaR25/median/currentGaR75/currentGaR95/
        tailRisk(high/elevated/moderate/low)/tailLabel/skewness/description.
        None — 데이터 부족 시.

    Example:
        >>> r = growthAtRisk([fci]*30, [gdp]*30, horizon=4)
        >>> r["tailRisk"], r["currentGaR5"]
        ('elevated', -1.5)

    Guide:
        tailRisk "high" (GaR5 < -2.0) = 1 년 후 침체 강한 신호. skewness 음수
        부호 + 절댓값 ↑ = 하방 꼬리 두꺼움 (risk-off regime).

    When:
        ``analyzeCrisis`` 내부 + AI "1 년 후 GDP 하방 리스크" 답변.

    How:
        시계열 정렬 → NaN 제거 → horizon shift → 분위 회귀 (quantile regression
        IWLS) → 현재 FCI 로 예측.

    Requires:
        ≥ 20 관측치 (FCI + GDP). NFCI (FRED) + GDP 분기 권장.

    Raises:
        없음 — 데이터 부족 시 None.

    See Also:
        - calcFCI : FCI 입력 생성
        - analyzeCrisis : 본 함수 호출 진입점

    AIContext:
        tailLabel + currentGaR5 + median 3 필드 인용으로 "GaR 5th -1.5% (주의),
        중위 +2.0%" 답변.

    LLM Specifications:
        AntiPatterns:
            - currentGaR5 만 인용 + median 무시 (중심 추세 손실)
            - 20 미만 관측치에 강한 단정
            - quantile 임의 변경 (기본 5/25/50/75/95 표준)
        OutputSchema:
            ``{currentGaR5, currentGaR25, median, currentGaR75, currentGaR95,
            tailRisk, tailLabel, skewness, description}`` 또는 None.
        Prerequisites: FCI + GDP 시계열 ≥ 20 분기.
        Freshness: 분기.
        Dataflow: 시계열 → shift → quantile regression → 분위 + tail risk.
        TargetMarkets: US (FCI + GDP). KR 동일 적용 가능.
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

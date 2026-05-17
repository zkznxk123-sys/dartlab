"""수익률 곡선 모델 — Nelson-Siegel 분해.

순수 데이터 + 판정 함수. numpy만 사용, 외부 의존성 없음.
core/ 계층 소속 — macro/rates에서 소비.

학술 근거:
- Nelson & Siegel (1987): "Parsimonious Modeling of Yield Curves"
- Diebold & Li (2006): "Forecasting the Term Structure of Government Bond Yields"
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class NelsonSiegelResult:
    """Nelson-Siegel 수익률 곡선 분해 결과."""

    beta0: float  # Level (장기 금리 수준)
    beta1: float  # Slope (기울기: 양수=정상, 음수=역전)
    beta2: float  # Curvature (곡률: 중기 볼록/오목)
    lamb: float  # λ (감쇠 파라미터)
    fitted: np.ndarray  # 피팅된 수익률
    residuals: np.ndarray  # 잔차
    rmse: float  # RMSE
    interpretation: str  # 해석
    description: str


def _nsFactorLoadings(tau: np.ndarray, lamb: float) -> np.ndarray:
    """Nelson-Siegel 팩터 로딩 행렬 (T×3).

    y(τ) = β0 × 1 + β1 × [(1-e^(-τ/λ))/(τ/λ)] + β2 × [(1-e^(-τ/λ))/(τ/λ) - e^(-τ/λ)]
    """
    x = tau / lamb
    x = np.maximum(x, 1e-10)  # 0 방지
    exp_x = np.exp(-x)
    f1 = np.ones_like(tau)
    f2 = (1 - exp_x) / x
    f3 = f2 - exp_x
    return np.column_stack([f1, f2, f3])


def nelsonSiegel(
    maturities: list[float] | np.ndarray,
    yields: list[float] | np.ndarray,
) -> NelsonSiegelResult:
    """Nelson-Siegel 모델로 수익률 곡선 분해.

    Capabilities:
        Nelson-Siegel (1987) 3 인자 모델 (β0=Level, β1=Slope, β2=Curvature) 을
        grid search λ (Diebold-Li 기본 1.5) + OLS 로 추정. 수익률곡선 정상/
        평탄/역전/가파른 정상 4 라벨 해석. scipy 없이 numpy 만 사용 — 경량.

    Args:
        maturities: 만기 (년) 리스트 (예: [0.25, 1, 2, 3, 5, 7, 10, 20, 30]).
        yields: 해당 만기 수익률 (%) 리스트.

    Returns:
        NelsonSiegelResult — beta0/beta1/beta2/lamb/fitted/residuals/rmse/
        interpretation(steep_normal/normal/flat/inverted)/description.

    Example:
        >>> r = nelsonSiegel([1, 2, 5, 10, 30], [4.5, 4.2, 3.8, 3.9, 4.1])
        >>> r.interpretation
        'normal'

    Guide:
        effective_slope = -β1 (장기-단기 ≈ -β1). 역전 (-0.5 미만) = 침체 경고.
        rmse > 0.5%p 면 모델 적합도 낮음 (만기 4 개 미만일 경우 흔함).

    When:
        ``analyzeRates`` 내부 (US 만) 또는 외부 호출자가 만기별 yield 직접
        제공 시.

    How:
        만기/yield → grid search λ 0.3~6.0 → OLS lstsq → 최저 RMSE → β →
        slope 해석 라벨.

    Requires:
        만기 ≥ 3 개. 일반적으로 8 개 (DGS1/2/3/5/7/10/20/30) 권장.

    Raises:
        없음 (만기 < 3 면 insufficient interpretation 반환).

    See Also:
        - decomposeLongRate : DKW 분해 (실질금리/BEI)
        - analyzeRates : yieldCurve 호출 진입점

    AIContext:
        interpretation 라벨 1 단어 + slope 값 인용으로 1 문장 답변 완성.

    LLM Specifications:
        AntiPatterns:
            - β1 부호 직역 (양수=정상 X). effective_slope = -β1.
            - 만기 3 개 미만에 강한 단정
            - rmse 미공개 + 모델 적합도 검증 누락
        OutputSchema:
            NelsonSiegelResult ``(beta0, beta1, beta2, lamb, fitted, residuals,
            rmse, interpretation, description)``.
        Prerequisites: 동일 시점 만기별 yield 데이터.
        Freshness: 일간 (FRED DGS 시리즈).
        Dataflow: 만기/yield → grid λ → OLS → 라벨.
        TargetMarkets: US (FRED DGS 풀세트). KR/JP 가능 (만기 데이터 제공 시).
    """
    tau = np.asarray(maturities, dtype=np.float64)
    y = np.asarray(yields, dtype=np.float64)

    # 유효 데이터만
    mask = ~(np.isnan(tau) | np.isnan(y))
    tau = tau[mask]
    y = y[mask]

    if len(tau) < 3:
        return NelsonSiegelResult(0, 0, 0, 1.0, np.array([]), np.array([]), 0, "insufficient", "데이터 3개 미만")

    # Grid search: λ = 0.5 ~ 5.0 (Diebold-Li 기본값 ~1.5)
    best_rmse = np.inf
    best_beta = np.zeros(3)
    best_lamb = 1.5

    for lamb in np.arange(0.3, 6.0, 0.1):
        X = _nsFactorLoadings(tau, lamb)
        # OLS: β = (X'X)^{-1} X'y
        try:
            beta = np.linalg.lstsq(X, y, rcond=None)[0]
        except np.linalg.LinAlgError:
            continue
        resid = y - X @ beta
        rmse = float(np.sqrt(np.mean(resid**2)))
        if rmse < best_rmse:
            best_rmse = rmse
            best_beta = beta
            best_lamb = lamb

    b0, b1, b2 = best_beta
    X_best = _nsFactorLoadings(tau, best_lamb)
    fitted = X_best @ best_beta
    residuals = y - fitted

    # 해석
    # β1: 양수 = 정상(단기>장기 spread 양수의 반대...). 실제: β1 ≈ -(장기-단기)
    # Nelson-Siegel에서 β1이 음수면 정상적 우상향, 양수면 역전
    # Slope = 장기 - 단기 ≈ β0 - (β0 + β1) = -β1
    effective_slope = -b1

    if effective_slope > 1.0:
        interp = "steep_normal"
        desc = f"수익률 곡선 가파른 정상 (기울기 {effective_slope:.2f}%p) — 경기 확장/인플레 기대"
    elif effective_slope > 0.0:
        interp = "normal"
        desc = f"수익률 곡선 정상 (기울기 {effective_slope:.2f}%p) — 정상적 시장"
    elif effective_slope > -0.5:
        interp = "flat"
        desc = f"수익률 곡선 평탄화 (기울기 {effective_slope:.2f}%p) — 경기 둔화 신호"
    else:
        interp = "inverted"
        desc = f"수익률 곡선 역전 (기울기 {effective_slope:.2f}%p) — 침체 경고"

    return NelsonSiegelResult(
        beta0=round(float(b0), 4),
        beta1=round(float(b1), 4),
        beta2=round(float(b2), 4),
        lamb=round(float(best_lamb), 2),
        fitted=fitted,
        residuals=residuals,
        rmse=round(best_rmse, 4),
        interpretation=interp,
        description=desc,
    )

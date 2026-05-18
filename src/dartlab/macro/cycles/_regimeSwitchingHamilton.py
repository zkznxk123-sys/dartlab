"""regimeSwitching 의 Hamilton MS-AR 모듈 — Markov-Switching Autoregressive 모델."""

from __future__ import annotations

from dataclasses import dataclass
from math import log, pi, sqrt

import numpy as np


@dataclass(frozen=True)
class HamiltonResult:
    """Hamilton Regime Switching 결과."""

    filteredProbs: np.ndarray  # (T, 2) — P(s_t=j | Y_t)
    smoothedProbs: np.ndarray  # (T, 2) — P(s_t=j | Y_T)
    currentRegime: int  # 0 또는 1 (smoothed 기준 최종 시점)
    currentProb: float  # 현재 regime의 확률
    regimeLabels: tuple[str, str]  # ("expansion", "contraction")
    params: dict  # 추정된 파라미터
    logLikelihood: float
    converged: bool
    iterations: int


def _gaussianDensity(y: float, mu: float, sigma: float) -> float:
    """정규분포 밀도 f(y | mu, sigma). 언더플로 방지를 위해 로그로 계산."""
    if sigma <= 0:
        return 1e-300
    z = (y - mu) / sigma
    log_density = -0.5 * log(2 * pi) - log(sigma) - 0.5 * z * z
    return max(np.exp(log_density), 1e-300)


def _ergodicProbs(p00: float, p11: float) -> np.ndarray:
    """정상 상태(ergodic) 확률: πP = π."""
    denom = 2.0 - p00 - p11
    if abs(denom) < 1e-10:
        return np.array([0.5, 0.5])
    pi0 = (1.0 - p11) / denom
    return np.array([pi0, 1.0 - pi0])


def _hamiltonFilter(
    y: np.ndarray,
    mu: np.ndarray,
    sigma: np.ndarray,
    phi: float,
    p00: float,
    p11: float,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Hamilton 필터 (forward recursion).

    Args:
        y: (T,) GDP 성장률 시계열
        mu: (2,) regime별 평균
        sigma: (2,) regime별 표준편차
        phi: AR(1) 계수
        p00, p11: 전이확률 (regime 유지 확률)

    Returns:
        filtered: (T, 2) — P(s_t=j | Y_t)
        predicted: (T, 2) — P(s_t=j | Y_{t-1})
        log_lik: 로그우도
    """
    T = len(y)
    P = np.array([[p00, 1 - p00], [1 - p11, p11]])  # 전이행렬

    filtered = np.zeros((T, 2))
    predicted = np.zeros((T, 2))

    xi = _ergodicProbs(p00, p11)
    log_lik = 0.0

    for t in range(T):
        # Prediction
        xi_pred = P.T @ xi
        xi_pred = np.maximum(xi_pred, 1e-10)
        xi_pred /= xi_pred.sum()
        predicted[t] = xi_pred

        # 조건부 밀도
        y[t] - mu[0] - (phi * y[t - 1] if t > 0 else 0.0)
        y[t] - mu[1] - (phi * y[t - 1] if t > 0 else 0.0)
        eta = np.array(
            [
                _gaussianDensity(y[t], mu[0] + (phi * y[t - 1] if t > 0 else 0.0), sigma[0]),
                _gaussianDensity(y[t], mu[1] + (phi * y[t - 1] if t > 0 else 0.0), sigma[1]),
            ]
        )

        # 주변 우도
        f_yt = xi_pred @ eta
        if f_yt < 1e-300:
            f_yt = 1e-300

        # Update (Bayes)
        xi = (xi_pred * eta) / f_yt
        xi = np.maximum(xi, 1e-10)
        xi /= xi.sum()
        filtered[t] = xi

        log_lik += log(f_yt)

    return filtered, predicted, log_lik


def _kimSmoother(
    filtered: np.ndarray,
    predicted: np.ndarray,
    p00: float,
    p11: float,
) -> np.ndarray:
    """Kim smoother (backward recursion).

    Returns:
        smoothed: (T, 2) — P(s_t=j | Y_T)
    """
    T = filtered.shape[0]
    P = np.array([[p00, 1 - p00], [1 - p11, p11]])
    smoothed = np.zeros((T, 2))
    smoothed[T - 1] = filtered[T - 1]

    for t in range(T - 2, -1, -1):
        for i in range(2):
            s = 0.0
            for j in range(2):
                pred_j = max(predicted[t + 1, j], 1e-10)
                s += P[i, j] * smoothed[t + 1, j] / pred_j
            smoothed[t, i] = filtered[t, i] * s
        # 정규화
        total = smoothed[t].sum()
        if total > 0:
            smoothed[t] /= total

    return smoothed


def hamiltonRegime(
    series: list[float] | np.ndarray,
    maxIter: int = 200,
    tol: float = 1e-6,
) -> HamiltonResult:
    """Hamilton Markov Regime Switching — EM 알고리즘 2-regime AR(1).

    Capabilities:
        Hamilton (1989) 2-regime Markov-Switching AR(1) 모델 EM 추정.
        y_t = μ_{s_t} + φ × y_{t-1} + ε_t, ε_t ~ N(0, σ²_{s_t}). regime 0 =
        확장 (높은 평균), regime 1 = 침체. 필터/스무더 확률 (Kim 1994) 함께
        반환. GDP/산업생산 분기 시계열에 표준 적용.

    Args:
        series: 시계열 (GDP 성장률 분기, 최소 10 기간 권장 20+).
        maxIter: EM 최대 반복 (기본 200).
        tol: 로그우도 수렴 기준 (기본 1e-6).

    Returns:
        HamiltonResult:
            - ``filteredProbs``/``smoothedProbs`` (np.ndarray T×2): regime
              확률 시계열.
            - ``currentRegime`` (int): 최신 regime (0/1).
            - ``currentProb`` (float): 최신 regime 확률.
            - ``regimeLabels`` (tuple): ("expansion", "contraction").
            - ``params`` (dict): μ, σ, φ, p00, p11.
            - ``logLikelihood`` (float): 최종 LL.
            - ``converged`` (bool) / ``iterations`` (int).

    Raises:
        없음 (T < 10 시 empty result 반환).

    Example:
        >>> r = hamiltonRegime([2.5, 2.8, -1.2, -0.5, 1.8, ...])
        >>> r.currentRegime, r.currentProb
        (0, 0.85)  # 85% 확률 확장 regime

    Guide:
        - smoothedProbs > 0.7 = 강한 regime 신호 (확장 또는 침체 확정).
        - 0.3 ~ 0.7 = 전환 구간 (uncertainty 큼).
        - 최소 20 분기 (5 년) 권장 — 단기 데이터는 regime 분리 약함.
        - p00/p11 (자기지속 확률) 0.9+ 면 regime persistent.

    See Also:
        - ``clevelandProbit``: 단변량 yield curve 기반
        - ``sahmRule``: 실업률 룰
        - ``conferenceBoardLEI``: LEI 합성지수

    When:
        ``analyzeSummary`` regime 축 (US GDP) 진입점. 분기 갱신.

    How:
        EM 초기값 (median split) → forward-backward filter → Kim smoother → 수렴 →
        params + smoothedProbs.

    Requires:
        시계열 ≥ 10 기간 (≥ 20 권장).

    AIContext:
        currentRegime + smoothedProb 함께. 확률 0.5 부근은 단정 금지 (전환
        구간). converged=False 면 결과 신뢰 낮음.

    LLM Specifications:
        AntiPatterns:
            - filteredProbs 와 smoothedProbs 혼동 — 후자가 회고적, 전자가
              실시간.
            - 짧은 시계열 (< 20 기간) 에 강한 단정.
        OutputSchema:
            ``HamiltonResult(filteredProbs: ndarray, smoothedProbs: ndarray,
              currentRegime: int, currentProb: float, regimeLabels: tuple,
              params: dict, logLikelihood: float, converged: bool,
              iterations: int)``.
        Prerequisites:
            시계열 ≥ 10 기간 (≥ 20 권장).
        Freshness:
            분기 (GDP 갱신 직후).
        Dataflow:
            series → 초기값 (median split) → EM (E: forward-backward, M:
            params 갱신) → 수렴 → 필터/스무더 확률.
        TargetMarkets: US (BEA GDP), KR (BOK GDP), 글로벌 분기 GDP.
    """
    y = np.asarray(series, dtype=np.float64)
    T = len(y)

    if T < 10:
        empty = np.full((T, 2), 0.5)
        return HamiltonResult(
            filteredProbs=empty,
            smoothedProbs=empty,
            currentRegime=0,
            currentProb=0.5,
            regimeLabels=("expansion", "contraction"),
            params={},
            logLikelihood=0.0,
            converged=False,
            iterations=0,
        )

    # ── 초기값 ──
    median = float(np.median(y))
    mu = np.array([float(np.mean(y[y >= median])), float(np.mean(y[y < median]))])
    sigma = np.array([float(np.std(y[y >= median])) + 0.01, float(np.std(y[y < median])) + 0.01])
    phi = 0.0
    p00 = 0.90
    p11 = 0.90

    # regime 0 = 확장 (높은 평균), regime 1 = 침체 (낮은 평균)
    if mu[0] < mu[1]:
        mu[0], mu[1] = mu[1], mu[0]
        sigma[0], sigma[1] = sigma[1], sigma[0]

    prev_ll = -np.inf
    converged = False

    for iteration in range(maxIter):
        # ── E-step ──
        filtered, predicted, log_lik = _hamiltonFilter(y, mu, sigma, phi, p00, p11)
        smoothed = _kimSmoother(filtered, predicted, p00, p11)

        # 수렴 체크
        if abs(log_lik - prev_ll) < tol:
            converged = True
            break
        prev_ll = log_lik

        # ── M-step ──
        w = smoothed  # (T, 2) — smoothed regime 확률

        # 전이확률 갱신 (joint smoothed approximation)
        P_mat = np.array([[p00, 1 - p00], [1 - p11, p11]])
        numer = np.zeros((2, 2))
        denom_p = np.zeros(2)
        for t in range(1, T):
            for i in range(2):
                for j in range(2):
                    joint = filtered[t - 1, i] * P_mat[i, j] * smoothed[t, j]
                    pred_j = max(predicted[t, j], 1e-10)
                    joint *= (smoothed[t, j] / max(filtered[t, j], 1e-10)) if filtered[t, j] > 1e-10 else 1.0
                    # 단순화: joint ≈ w[t-1, i] * P[i,j] * (w[t,j] / pred[t,j])
                    joint_simple = w[t - 1, i] * P_mat[i, j] * w[t, j] / pred_j
                    numer[i, j] += joint_simple
                denom_p[i] += w[t - 1, i]

        for i in range(2):
            if denom_p[i] > 0:
                for j in range(2):
                    numer[i, j] /= denom_p[i]
        # 정규화
        for i in range(2):
            row_sum = numer[i].sum()
            if row_sum > 0:
                numer[i] /= row_sum
        p00 = np.clip(numer[0, 0], 0.01, 0.99)
        p11 = np.clip(numer[1, 1], 0.01, 0.99)

        # AR 계수 (가중 OLS)
        wx = 0.0
        wxx = 0.0
        for t in range(1, T):
            for j in range(2):
                resid = y[t] - mu[j]
                x = y[t - 1] - mu[j]
                wx += w[t, j] * resid * x
                wxx += w[t, j] * x * x
        if wxx > 0:
            phi = np.clip(wx / wxx, -0.95, 0.95)

        # Regime 평균
        for j in range(2):
            numer_mu = 0.0
            denom_mu = 0.0
            for t in range(T):
                ar_term = phi * y[t - 1] if t > 0 else 0.0
                numer_mu += w[t, j] * (y[t] - ar_term)
                denom_mu += w[t, j]
            if denom_mu > 0:
                mu[j] = numer_mu / denom_mu

        # Regime 분산
        for j in range(2):
            numer_var = 0.0
            denom_var = 0.0
            for t in range(T):
                ar_term = phi * y[t - 1] if t > 0 else 0.0
                resid = y[t] - mu[j] - ar_term
                numer_var += w[t, j] * resid * resid
                denom_var += w[t, j]
            if denom_var > 0:
                sigma[j] = max(sqrt(numer_var / denom_var), 0.01)

        # regime 0이 항상 확장(높은 평균)이도록 유지
        if mu[0] < mu[1]:
            mu[0], mu[1] = mu[1], mu[0]
            sigma[0], sigma[1] = sigma[1], sigma[0]
            p00, p11 = p11, p00
            filtered = filtered[:, ::-1]
            smoothed = smoothed[:, ::-1]
            predicted = predicted[:, ::-1]

    # 최종 필터/스무더
    filtered, predicted, log_lik = _hamiltonFilter(y, mu, sigma, phi, p00, p11)
    smoothed = _kimSmoother(filtered, predicted, p00, p11)

    current_regime = int(np.argmax(smoothed[-1]))
    current_prob = float(smoothed[-1, current_regime])

    return HamiltonResult(
        filteredProbs=filtered,
        smoothedProbs=smoothed,
        currentRegime=current_regime,
        currentProb=round(current_prob, 4),
        regimeLabels=("expansion", "contraction"),
        params={
            "mu_expansion": round(float(mu[0]), 4),
            "mu_contraction": round(float(mu[1]), 4),
            "sigma_expansion": round(float(sigma[0]), 4),
            "sigma_contraction": round(float(sigma[1]), 4),
            "phi": round(float(phi), 4),
            "p_stay_expansion": round(float(p00), 4),
            "p_stay_contraction": round(float(p11), 4),
        },
        logLikelihood=round(log_lik, 2),
        converged=converged,
        iterations=iteration + 1,
    )

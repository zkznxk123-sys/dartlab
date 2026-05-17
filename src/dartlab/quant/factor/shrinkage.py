"""Covariance Shrinkage 3종 — OAS, Constant-Correlation, RMT denoising.

기존 quant/portfolio.py 의 _ledoit_wolf_shrinkage (LW 1종) 보완.

학술 :
    - Chen, Wiesel, Hero (2010) — OAS (Oracle Approximating Shrinkage)
    - Ledoit & Wolf (2003) — Constant-Correlation target
    - Marchenko-Pastur (1967) — RMT eigenvalue denoising
      (Lopez de Prado AFML Ch.2 응용)
"""

from __future__ import annotations

import numpy as np


def shrinkOAS(returns: np.ndarray) -> dict:
    """OAS shrinkage (Chen-Wiesel-Hero 2010) — 더 강한 oracle bound.

    Capabilities:
        - Oracle Approximating Shrinkage (OAS) → sample cov 를 scaled identity 로 축소
        - shrinkageRatio ρ 자동 추정 + 결과 cov 매트릭스

    Args:
        returns: T × N 일별 수익률 매트릭스.

    Returns:
        dict — cov / shrinkageRatio / target / n / t.

    Guide:
        Ledoit-Wolf 보다 oracle bound 가 더 강함. 작은 표본 (T<N) 에서도 안정적.

    When:
        Portfolio cov 추정 + AI 표본 작은 cov 안정화 답변.

    How:
        sample_cov 계산 → trace target → OAS 공식 적용.

    Requires:
        returns T × N 매트릭스.

    Raises:
        없음 — den ≤ 0 시 ρ=0.

    Example:
        >>> r = shrinkOAS(returns)
        >>> r["shrinkageRatio"]
        0.18

    See Also:
        - shrinkConstantCorrelation : 대안 target
        - denoiseRMT : eigenvalue 기반

    AIContext:
        "cov 추정 안정화 방법" 답변 시 shrinkageRatio 인용.
    """
    R = np.asarray(returns, dtype=np.float64)
    T, N = R.shape
    R_centered = R - R.mean(axis=0)
    sample_cov = (R_centered.T @ R_centered) / max(T - 1, 1)
    trace = np.trace(sample_cov)
    target = (trace / N) * np.eye(N)

    # OAS formula
    num = (1 - 2 / N) * np.trace(sample_cov @ sample_cov) + trace**2
    den = (T + 1 - 2 / N) * (np.trace(sample_cov @ sample_cov) - trace**2 / N)
    if den <= 0:
        rho = 0.0
    else:
        rho = min(num / den, 1.0)

    shrunk = rho * target + (1 - rho) * sample_cov
    return {
        "cov": shrunk,
        "shrinkageRatio": round(float(rho), 4),
        "target": "scaled identity (avg variance)",
        "n": N,
        "t": T,
    }


def shrinkConstantCorrelation(returns: np.ndarray) -> dict:
    """Constant-Correlation shrinkage — Ledoit-Wolf (2003).

    Target = 평균 상관 ρ_avg 가 모든 off-diagonal 인 covariance.

    Capabilities:
        - sample cov 의 평균 off-diagonal 상관 ρ_avg 추출 → target = ρ_avg × σσ
        - 단순화된 shrinkage intensity (LW 공식 압축형)

    Args:
        returns: T × N.

    Returns:
        dict — cov / shrinkageRatio / avgCorrelation / target / n / t.

    Guide:
        Ledoit-Wolf 2003 표준. 자산 간 비슷한 상관 구조 가정 시 적합.

    When:
        Portfolio cov + AI 상관 평균 답변.

    How:
        sample cov → diag scale → off-diag 평균 → target reconstruct → rho 적용.

    Requires:
        returns T × N + N ≥ 2.

    Raises:
        없음.

    Example:
        >>> r = shrinkConstantCorrelation(returns)
        >>> r["avgCorrelation"]
        0.32

    See Also:
        - shrinkOAS : OAS 변형
        - denoiseRMT : RMT 기반

    AIContext:
        "자산 간 평균 상관" 답변 시 avgCorrelation 인용.
    """
    R = np.asarray(returns, dtype=np.float64)
    T, N = R.shape
    R_centered = R - R.mean(axis=0)
    sample_cov = (R_centered.T @ R_centered) / max(T - 1, 1)

    diag = np.sqrt(np.diag(sample_cov))
    diag_safe = np.where(diag < 1e-10, 1e-10, diag)
    corr = sample_cov / np.outer(diag_safe, diag_safe)

    # average off-diagonal correlation
    upper = corr[np.triu_indices(N, k=1)]
    rho_avg = float(np.mean(upper))

    # target: ρ_avg off-diagonal, σ_i σ_j scale
    target = np.outer(diag_safe, diag_safe) * rho_avg
    np.fill_diagonal(target, np.diag(sample_cov))

    # shrinkage intensity (LW formula 단순화)
    diff = sample_cov - target
    pi_hat = np.sum(diff**2)
    rho_shrink = min(0.5, max(0.0, 1.0 / (1 + T / max(pi_hat, 1e-10))))

    shrunk = rho_shrink * target + (1 - rho_shrink) * sample_cov
    return {
        "cov": shrunk,
        "shrinkageRatio": round(rho_shrink, 4),
        "avgCorrelation": round(rho_avg, 4),
        "target": "constant correlation",
        "n": N,
        "t": T,
    }


def denoiseRMT(returns: np.ndarray, *, alpha: float = 0.0) -> dict:
    """Marchenko-Pastur 기반 eigenvalue denoising (AFML Ch.2.6).

    1. sample_cov 의 eigenvalue λ_i 분리
    2. Marchenko-Pastur 이론: q = T/N, λ_+ = σ²(1+√(1/q))²
    3. λ_i < λ_+ 인 eigenvalue → noise (평균값으로 대체)
    4. λ_i > λ_+ → signal (보존)
    5. α 비율로 noise 부분 shrinkage

    Args:
        returns: T × N.
        alpha: 0~1 noise eigenvalue shrinkage 강도. 0 = 평균 대체, 1 = 그대로.

    Returns:
        dict — cov (denoised) / qRatio / lambdaPlus / noiseEigenCount / signalEigenCount /
        topEigenvalues / interpretation. T ≤ N 시 ``{"error": ...}``.

    Capabilities:
        - Marchenko-Pastur 임계로 noise / signal eigenvalue 분리 + noise 평균 대체
        - alpha 보간으로 부분 보존도 가능

    Guide:
        Lopez de Prado AFML Ch.2.6 표준. q ≥ 2 (T ≥ 2N) 권장 — 안정적 임계.

    When:
        Cov 노이즈 제거 + AI "추정 오차" 답변.

    How:
        standardize → corr eigendecomposition → MP threshold → noise mask → 평균 대체 → cov 재구성.

    Requires:
        T > N (overdetermined sample).

    Raises:
        없음 — T ≤ N 시 error dict.

    Example:
        >>> r = denoiseRMT(returns)
        >>> r["noiseEigenCount"], r["signalEigenCount"]
        (28, 5)

    See Also:
        - shrinkOAS : scaled identity target
        - shrinkConstantCorrelation : avg corr target

    AIContext:
        "이 cov 추정 신뢰" 답변 시 signal vs noise eigenvalue 비율 인용.
    """
    R = np.asarray(returns, dtype=np.float64)
    T, N = R.shape
    if T <= N:
        return {"error": "T must be > N for RMT denoising"}

    R_centered = R - R.mean(axis=0)
    # standardize for correlation
    std = R_centered.std(axis=0, ddof=1)
    std_safe = np.where(std < 1e-10, 1e-10, std)
    Z = R_centered / std_safe
    corr = (Z.T @ Z) / max(T - 1, 1)
    np.fill_diagonal(corr, 1)

    eig_vals, eig_vecs = np.linalg.eigh(corr)
    # MP threshold (variance assumed = 1 since standardized)
    q = T / N
    lambda_plus = (1 + 1 / np.sqrt(q)) ** 2

    noise_mask = eig_vals < lambda_plus
    signal_mask = ~noise_mask

    if noise_mask.sum() > 0:
        avg_noise_lambda = float(eig_vals[noise_mask].mean())
        denoised_eig = eig_vals.copy()
        denoised_eig[noise_mask] = (1 - alpha) * avg_noise_lambda + alpha * eig_vals[noise_mask]
    else:
        denoised_eig = eig_vals.copy()

    # reconstruct correlation
    corr_denoised = (eig_vecs * denoised_eig) @ eig_vecs.T
    # cov = D @ corr_denoised @ D
    D = np.diag(std_safe)
    cov_denoised = D @ corr_denoised @ D

    return {
        "cov": cov_denoised,
        "n": N,
        "t": T,
        "qRatio": round(q, 3),
        "lambdaPlus": round(float(lambda_plus), 4),
        "noiseEigenCount": int(noise_mask.sum()),
        "signalEigenCount": int(signal_mask.sum()),
        "topEigenvalues": [round(float(v), 4) for v in sorted(eig_vals, reverse=True)[:5]],
        "interpretation": (
            f"N={N}, T={T}, q={round(q, 2)}, λ_+={round(float(lambda_plus), 3)}. "
            f"signal eigenvalues {int(signal_mask.sum())} / noise {int(noise_mask.sum())}. "
            "noise eigenvalue 평균 대체로 estimation noise 제거."
        ),
    }

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

    Args:
        returns: T × N 일별 수익률.

    Returns:
        dict with cov, shrinkageRatio, target, n, t
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
        dict with cov (denoised), eigenSpectrum, noiseEigenCount, signalEigenCount
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

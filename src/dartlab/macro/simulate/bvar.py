"""Reduced-form BVAR 추정 — 자연켤레 Minnesota prior (dummy observations).

Litterman(1986) Minnesota prior + Bańbura-Giannone-Reichlin(2010) dummy-observation
자연켤레. numpy only(macro 엔진 하우스 스타일 — 외부 통계 라이브러리 없음).

NIW 사후(계수 행렬정규 + Σ 역위샤트)라 파라미터 불확실성 draw 가능(fan.py 소비).
짧은 표본 정규화 = Minnesota shrinkage(분기·월 혼합 거시패널 과적합 차단).
"""

from __future__ import annotations

import numpy as np

from dartlab.macro.simulate._types import DELTA_BY_TRANSFORM, BvarFit, VarSpec


def _arResidStd(panel: np.ndarray, p: int) -> np.ndarray:
    """변수별 단변량 AR(p) 잔차 표준편차 — Minnesota prior 스케일 σ_i."""
    t, n = panel.shape
    sig = np.empty(n)
    for i in range(n):
        y = panel[p:, i]
        x = np.column_stack([panel[p - lag : t - lag, i] for lag in range(1, p + 1)] + [np.ones(t - p)])
        beta, *_ = np.linalg.lstsq(x, y, rcond=None)
        resid = y - x @ beta
        sig[i] = float(np.std(resid, ddof=x.shape[1])) if t - p > x.shape[1] else float(np.std(resid))
        if not np.isfinite(sig[i]) or sig[i] <= 0:
            sig[i] = float(np.std(panel[:, i])) or 1.0
    return sig


def _buildYX(panel: np.ndarray, p: int) -> tuple[np.ndarray, np.ndarray]:
    """VAR(p) 회귀행렬. Y=(T-p, n), X=(T-p, n·p+1)[lag1..lagp, 절편(마지막 열)]."""
    t, n = panel.shape
    y = panel[p:]
    rows = []
    for ti in range(p, t):
        row: list[float] = []
        for lag in range(1, p + 1):
            row.extend(panel[ti - lag])
        row.append(1.0)
        rows.append(row)
    return y, np.asarray(rows, dtype=float)


def _minnesotaDummies(specs: tuple[VarSpec, ...], sigma: np.ndarray, p: int, lam: float, eps: float):
    """Minnesota dummy observations(BGR 2010 핵심 2블록 + 절편 diffuse). lag 감쇠 l^1."""
    n = len(specs)
    k = n * p + 1
    delta = np.array([DELTA_BY_TRANSFORM[s.transform] for s in specs])

    yd1 = np.zeros((n * p, n))
    xd1 = np.zeros((n * p, k))
    for lag in range(1, p + 1):
        r0 = (lag - 1) * n
        xd1[r0 : r0 + n, (lag - 1) * n : lag * n] = lag * np.diag(sigma) / lam
        if lag == 1:
            yd1[0:n, :] = np.diag(delta * sigma) / lam
    yd2 = np.diag(sigma)
    xd2 = np.zeros((n, k))
    yd3 = np.zeros((1, n))
    xd3 = np.zeros((1, k))
    xd3[0, k - 1] = 1.0 / eps

    return np.vstack([yd1, yd2, yd3]), np.vstack([xd1, xd2, xd3])


def estimateBvar(
    panel: np.ndarray,
    specs: tuple[VarSpec, ...],
    p: int = 6,
    lam: float = 0.2,
    eps: float = 1e-4,
    lastLevels: np.ndarray | None = None,
    endYm: str = "",
) -> BvarFit:
    """자연켤레 Minnesota BVAR 추정 → NIW 사후.

    Args:
        panel: (T, n) 정상성 변환 끝난 패널(열 순서 = specs).
        specs: 변수 사양.
        p: lag 차수(기본 6개월).
        lam: 전체 tightness(작을수록 prior 강함, 밴드↓).
        eps: 절편 diffuse(작을수록 절편 prior 약함).
        lastLevels: (n,) 추정 끝 원시 레벨(logdiff 환산용). None 이면 0.
        endYm: 추정 마지막 'YYYY-MM'.

    Returns:
        BvarFit — bPost/sPost/nuPost/xtxInv/sigmaHat 등.

    Raises:
        ValueError: panel 열 수와 specs 길이 불일치.
    """
    t, n = panel.shape
    if n != len(specs):
        raise ValueError("panel 열 수와 specs 길이 불일치")
    sigma = _arResidStd(panel, p)
    y, x = _buildYX(panel, p)
    yd, xd = _minnesotaDummies(specs, sigma, p, lam, eps)

    xs = np.vstack([x, xd])
    ys = np.vstack([y, yd])
    xtxInv = np.linalg.inv(xs.T @ xs)
    bPost = xtxInv @ (xs.T @ ys)
    resid = ys - xs @ bPost
    sPost = resid.T @ resid
    nuPost = xs.shape[0] - (n * p + 1)
    sigmaHat = sPost / max(nuPost - n - 1, 1)

    levels = np.zeros(n) if lastLevels is None else np.asarray(lastLevels, float)
    return BvarFit(bPost, sPost, float(nuPost), xtxInv, sigmaHat, p, n, tuple(specs), levels, endYm, t)


def maxCompanionModulus(fit: BvarFit) -> float:
    """VAR(p) companion 행렬 최대 고유값 모듈러스. < 1 = 안정(정상 VAR). fail-closed 게이트."""
    n, p = fit.n, fit.p
    lag = fit.bPost[: n * p, :]
    top = np.hstack([lag[(i - 1) * n : i * n, :].T for i in range(1, p + 1)])
    comp = np.zeros((n * p, n * p))
    comp[:n, :] = top
    if p > 1:
        comp[n:, : n * (p - 1)] = np.eye(n * (p - 1))
    return float(np.max(np.abs(np.linalg.eigvals(comp))))

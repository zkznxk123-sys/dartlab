"""Forward 분위 팬 — NIW 사후 draw × 충격 draw forward 반복 → 변수·시점별 분위.

파라미터 불확실성(사후 draw)을 포함해야 밴드가 정직(좁은 밴드=거짓확신 가드, PRD 00 §5).
결정론 = np.random.default_rng(seed) 로컬 인스턴스(전역 seed 금지).
"""

from __future__ import annotations

import numpy as np

from dartlab.macro.simulate._types import BvarFit


def _drawInvWishart(scale: np.ndarray, dof: float, rng: np.random.Generator) -> np.ndarray:
    """역위샤트 draw(Bartlett 분해, numpy only). Σ ~ IW(scale, dof)."""
    n = scale.shape[0]
    chol = np.linalg.cholesky(np.linalg.inv(scale))
    a = np.zeros((n, n))
    for i in range(n):
        a[i, i] = np.sqrt(rng.chisquare(dof - i))
        for j in range(i):
            a[i, j] = rng.standard_normal()
    la = chol @ a
    return np.linalg.inv(la @ la.T)


def _drawCoef(bPost: np.ndarray, xtxInv: np.ndarray, sigma: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """행렬정규 draw: B ~ MN(bPost, Σ ⊗ xtxInv)."""
    la = np.linalg.cholesky(xtxInv)
    lb = np.linalg.cholesky(sigma)
    z = rng.standard_normal(bPost.shape)
    return bPost + la @ z @ lb.T


def _forwardPath(
    bDraw: np.ndarray, history: np.ndarray, p: int, n: int, horizon: int, shocks: np.ndarray
) -> np.ndarray:
    """단일 draw forward 시뮬 — VAR(p) 반복. history=(p,n) 오래된→최신. 반환 (horizon,n)."""
    lagCoef = bDraw[: n * p, :]
    intercept = bDraw[n * p, :]
    buf = [history[i].copy() for i in range(p)]
    out = np.empty((horizon, n))
    for h in range(horizon):
        x: list[float] = []
        for lag in range(1, p + 1):
            x.extend(buf[-lag])
        yhat = np.asarray(x) @ lagCoef + intercept + shocks[h]
        out[h] = yhat
        buf.append(yhat)
    return out


def forwardFan(
    fit: BvarFit,
    history: np.ndarray,
    horizon: int = 12,
    draws: int = 2000,
    seed: int = 20260624,
    quantiles: tuple[int, ...] = (5, 25, 50, 75, 95),
) -> dict:
    """forward 분위 팬.

    Args:
        fit: BVAR 적합.
        history: (>=p, n) 정상성 변환 패널 최근값(끝이 최신).
        horizon: 예측 개월.
        draws: 사후·충격 draw 수.
        seed: 결정론 시드(로컬 rng).
        quantiles: 산출 분위(%).

    Returns:
        dict[varLabel → {transform, label, seriesId, q5.., mean, level_q5..(logdiff100 한정)}].
    """
    rng = np.random.default_rng(seed)
    n, p = fit.n, fit.p
    hist = history[-p:]
    paths = np.empty((draws, horizon, n))
    for d in range(draws):
        sigma = _drawInvWishart(fit.sPost, fit.nuPost, rng)
        bDraw = _drawCoef(fit.bPost, fit.xtxInv, sigma, rng)
        shocks = rng.standard_normal((horizon, n)) @ np.linalg.cholesky(sigma).T
        paths[d] = _forwardPath(bDraw, hist, p, n, horizon, shocks)

    out: dict = {}
    for i, spec in enumerate(fit.specs):
        vi = paths[:, :, i]
        rec: dict = {"transform": spec.transform, "label": spec.label, "seriesId": spec.seriesId}
        for q in quantiles:
            rec[f"q{q}"] = np.percentile(vi, q, axis=0).tolist()
        rec["mean"] = vi.mean(axis=0).tolist()
        if spec.transform == "logdiff100":
            lvl0 = float(fit.lastLevels[i])
            for q in quantiles:
                g = np.array(rec[f"q{q}"]) / 100.0
                rec[f"level_q{q}"] = (lvl0 * np.exp(np.cumsum(g))).tolist()
        out[spec.label] = rec
    return out

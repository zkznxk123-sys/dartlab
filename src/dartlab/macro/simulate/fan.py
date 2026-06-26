"""Forward 분위 팬 — 해석적(analytical) 예측오차 분산 밴드.

VAR(p) 다단 예측오차 분산 Σ_h = Σ_{j=0}^{h-1} Φ_j Σ Φ_j^T (Φ_j = companion MA 계수)를
닫힌형으로 누적 → Gaussian 분위 밴드. 난수·draw 없음 → *결정론·재현 정확*이라 같은 수식을
터미널 TS 로 포팅하면 Python 과 byte 수준 일치(golden parity). 파라미터(계수) 불확실성은
제외(점추정 분산) — 보정(calibration)으로 검증, 미달 시 inflation.

근거: Lütkepohl(2005) New Introduction to Multiple Time Series Analysis §2.2 예측오차 분산.
"""

from __future__ import annotations

import numpy as np

from dartlab.macro.simulate._types import BvarFit

# 표준정규 분위 z 값(고정 분위 집합) — numpy only(scipy.ppf 회피, TS 와 동일 상수).
_Z = {5: -1.6448536, 10: -1.2815516, 25: -0.6744898, 50: 0.0, 75: 0.6744898, 90: 1.2815516, 95: 1.6448536}


def _companion(fit: BvarFit) -> np.ndarray:
    """VAR(p) companion 행렬 (n·p, n·p)."""
    n, p = fit.n, fit.p
    lag = fit.bPost[: n * p, :]
    top = np.hstack([lag[(i - 1) * n : i * n, :].T for i in range(1, p + 1)])
    comp = np.zeros((n * p, n * p))
    comp[:n, :] = top
    if p > 1:
        comp[n:, : n * (p - 1)] = np.eye(n * (p - 1))
    return comp


def _meanPath(fit: BvarFit, history: np.ndarray, horizon: int) -> np.ndarray:
    """VAR(p) 평균 경로 forward — (horizon, n)."""
    n, p = fit.n, fit.p
    lagCoef = fit.bPost[: n * p, :]
    intercept = fit.bPost[n * p, :]
    hist = history[-p:]
    buf = [hist[i].copy() for i in range(p)]
    out = np.empty((horizon, n))
    for h in range(horizon):
        x: list[float] = []
        for lag in range(1, p + 1):
            x.extend(buf[-lag])
        yhat = np.asarray(x) @ lagCoef + intercept
        out[h] = yhat
        buf.append(yhat)
    return out


def companionMA(fit: BvarFit, horizon: int) -> list[np.ndarray]:
    """VAR(p) MA 계수 Φ_0..Φ_{horizon-1} (각 n×n). Φ_h = J C^h J^T.

    예측오차 분산(fan)과 조건부 예측(scenarioPath) 이 공유하는 닻 — 한 곳에서 산출해 drift 차단.
    """
    n, p = fit.n, fit.p
    comp = _companion(fit)
    sel = np.zeros((n, n * p))
    sel[:, :n] = np.eye(n)  # J: companion 상태 → 관측 n
    coefs: list[np.ndarray] = []
    cj = np.eye(n * p)  # C^0
    for _ in range(horizon):
        coefs.append(sel @ cj @ sel.T)
        cj = cj @ comp
    return coefs


def _forecastSE(fit: BvarFit, horizon: int) -> np.ndarray:
    """다단 예측오차 표준오차 — (horizon, n). Σ_h = Σ_{j=0}^{h-1} Φ_j Σ Φ_j^T 누적."""
    coefs = companionMA(fit, horizon)
    sigma = fit.sigmaHat
    se = np.empty((horizon, fit.n))
    accum = np.zeros((fit.n, fit.n))
    for h in range(horizon):
        phi = coefs[h]  # Φ_h (n, n)
        accum = accum + phi @ sigma @ phi.T
        se[h] = np.sqrt(np.maximum(np.diag(accum), 0.0))
    return se


def forwardFan(
    fit: BvarFit,
    history: np.ndarray,
    horizon: int = 12,
    quantiles: tuple[int, ...] = (5, 25, 50, 75, 95),
    histMonths: int = 18,
) -> dict:
    """해석적 forward 분위 팬(결정론).

    Args:
        fit: BVAR 적합.
        history: (>=p, n) 정상성 변환 패널 최근값(끝이 최신).
        horizon: 예측 개월.
        quantiles: 산출 분위(%). _Z 키 부분집합.
        histMonths: 차트 연결용 과거 실적 개월(변환 단위).

    Returns:
        dict[varLabel → {transform, label, seriesId, history, q5.., mean, level_q5..(logdiff100 한정)}].
    """
    mean = _meanPath(fit, history, horizon)  # (horizon, n)
    se = _forecastSE(fit, horizon)  # (horizon, n)

    out: dict = {}
    for i, spec in enumerate(fit.specs):
        rec: dict = {"transform": spec.transform, "label": spec.label, "seriesId": spec.seriesId}
        rec["history"] = history[-histMonths:, i].tolist()
        rec["mean"] = mean[:, i].tolist()
        for q in quantiles:
            band = mean[:, i] + _Z[q] * se[:, i]
            rec[f"q{q}"] = band.tolist()
        if spec.transform == "logdiff100":
            lvl0 = float(fit.lastLevels[i])
            for q in quantiles:
                g = np.array(rec[f"q{q}"]) / 100.0
                rec[f"level_q{q}"] = (lvl0 * np.exp(np.cumsum(g))).tolist()
        out[spec.label] = rec
    return out

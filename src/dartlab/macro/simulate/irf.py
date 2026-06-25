"""충격반응(IRF) — Cholesky 직교화 MA(∞) 전개.

⚠ 정직 경고(개념검증 실측): 재귀(Cholesky)식별 IRF 의 *방향부호*는 표본·식별 순서에
취약하다(price puzzle·output puzzle — 교과서적 아티팩트). 따라서 본 IRF 는 "재귀식별·예시"
caveat 와 함께만 표면화하고, 구조적 부호 truth 로 쓰지 않는다. 게이트=안정성(bvar.maxCompanionModulus).
구조 IRF 가 필요하면 sign-restriction 식별이 정공(차기 단계).
"""

from __future__ import annotations

import numpy as np

from dartlab.macro.simulate._types import BvarFit


def impulseResponse(fit: BvarFit, horizon: int = 24, shockVar: int = 0, shockSize: float | None = None) -> dict:
    """Cholesky 직교화 IRF.

    Args:
        fit: BVAR 적합.
        horizon: 반응 개월(h0..horizon).
        shockVar: 충격 변수 인덱스(재귀 순서 = specs 순서).
        shockSize: None 이면 1 표준편차, 값이면 shockVar 를 그만큼.

    Returns:
        dict[varLabel → [h0, h1, ...]] (변환 단위 반응) + key 'caveat'.
    """
    n, p = fit.n, fit.p
    lchol = np.linalg.cholesky(fit.sigmaHat)
    e = np.zeros(n)
    e[shockVar] = 1.0
    impact = lchol @ e
    if shockSize is not None:
        impact = impact / lchol[shockVar, shockVar] * shockSize

    lagCoef = fit.bPost[: n * p, :]
    buf = [np.zeros(n) for _ in range(p)]
    resp = np.empty((horizon + 1, n))
    resp[0] = impact
    buf.append(impact)
    for h in range(1, horizon + 1):
        x: list[float] = []
        for lag in range(1, p + 1):
            x.extend(buf[-lag])
        yhat = np.asarray(x) @ lagCoef
        resp[h] = yhat
        buf.append(yhat)

    out: dict = {spec.label: resp[:, i].tolist() for i, spec in enumerate(fit.specs)}
    out["caveat"] = "recursive-identification·illustrative"  # 구조 부호 truth 아님
    return out

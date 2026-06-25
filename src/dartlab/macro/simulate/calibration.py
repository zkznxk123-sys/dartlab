"""팬 보정(calibration) 측정 — held-out walk-forward coverage.

정직 척추(PRD 00 §5·02 §6): forward fan 이 *보정*됐는지 out-of-sample 로 증명.
명목 80% 밴드의 실제 피복률(coverage)을 rolling re-estimation 으로 측정 — under-coverage
(거짓확신)가 위험, over-coverage(보수적)는 정직한 방향. macroBacktest.walkForwardBacktest
(침체 precision/recall, 이진)의 *분포* 대칭 — 같은 look-ahead 차단 규율.

⚠ 비용: 시장당 수십 cutoff × 수백 draw → 수십 초. 빌드 hot path 아님(운영자/주기 측정).
"""

from __future__ import annotations

import numpy as np

from dartlab.macro.simulate._panel import buildPanel
from dartlab.macro.simulate.bvar import estimateBvar, maxCompanionModulus
from dartlab.macro.simulate.fan import forwardFan


def measureCoverage(
    x: np.ndarray,
    specs,
    *,
    horizon: int = 6,
    minTrain: int = 180,
    step: int = 6,
    lag: int = 6,
    lam: float = 0.2,
    lastLevels: np.ndarray | None = None,
    endYm: str = "",
) -> tuple[dict[str, float], int, int]:
    """순수 walk-forward coverage 측정(데이터 I/O 무관, 테스트 가능).

    x=(T, n) 정상성 패널. 각 cutoff 에서 [:c+1] 추정 → horizon 후 실현값이 80% 밴드 안인지.
    반환 (변수별 coverage, 총덮음, 총전체).
    """
    n = x.shape[0]
    hits = {s.label: [0, 0] for s in specs}  # [덮음, 전체]
    for c in range(minTrain, n - horizon, step):
        fit = estimateBvar(x[: c + 1], specs, p=lag, lam=lam, lastLevels=lastLevels, endYm=endYm)
        if maxCompanionModulus(fit) >= 1.0:
            continue
        fan = forwardFan(fit, x[: c + 1], horizon=horizon, quantiles=(10, 50, 90))
        for i, s in enumerate(specs):
            lo = fan[s.label]["q10"][horizon - 1]
            hi = fan[s.label]["q90"][horizon - 1]
            realized = float(x[c + horizon, i])
            hits[s.label][1] += 1
            if lo <= realized <= hi:
                hits[s.label][0] += 1
    cov = {lab: (v[0] / v[1]) for lab, v in hits.items() if v[1]}
    allHits = sum(v[0] for v in hits.values())
    allTot = sum(v[1] for v in hits.values())
    return cov, allHits, allTot


def fanCalibration(
    market: str = "US",
    *,
    horizon: int = 6,
    minTrain: int = 180,
    step: int = 6,
    lag: int = 6,
    lam: float = 0.2,
) -> dict:
    """held-out walk-forward 80% 밴드 coverage 측정(해석적 fan·결정론).

    Args:
        market: 'US' | 'KR'.
        horizon: 평가 예측 개월(기본 6).
        minTrain: 최소 학습 관측(기본 180 ≈ 15년).
        step: cutoff 간격(개월).
        lag: VAR lag. lam: Minnesota tightness.

    Returns:
        dict — status('calibrated'|'...표시 보류') · coverage80(overall) · byVar · minVar ·
        points · note. status='calibrated' 조건 = overall∈[0.72,0.90] ∧ under-coverage 0(≥0.70).

    Raises:
        ValueError: 미지원 market.
    """
    from dartlab.macro.simulate.simulate import _MARKET_SPECS

    mk = market.upper()
    if mk not in _MARKET_SPECS:
        raise ValueError("market 은 'US' 또는 'KR' 만 지원합니다.")
    specs = _MARKET_SPECS[mk]["specs"]

    from dartlab.macro.seriesFetch import getGather

    panel, missing = buildPanel(getGather(None), specs, minObs=minTrain)
    if panel is None:
        return {"status": "표본 부족·표시 보류", "missing": missing}

    if panel.panel.shape[0] <= minTrain + horizon:
        return {
            "status": "표본 부족·표시 보류",
            "missing": [{"id": "panel", "reason": f"행 {panel.panel.shape[0]} ≤ {minTrain + horizon}"}],
        }

    cov, allHits, allTot = measureCoverage(
        panel.panel,
        specs,
        horizon=horizon,
        minTrain=minTrain,
        step=step,
        lag=lag,
        lam=lam,
        lastLevels=panel.lastLevels,
        endYm=panel.endYm,
    )
    if not cov:
        return {"status": "측정 불가·표시 보류"}
    overall = allHits / allTot
    minVar = min(cov.values())
    calibrated = (0.72 <= overall <= 0.90) and (minVar >= 0.70)
    return {
        "status": "calibrated" if calibrated else "uncalibrated·표시 보류",
        "coverage80": round(overall, 3),
        "byVar": {k: round(v, 3) for k, v in cov.items()},
        "minVar": round(minVar, 3),
        "points": allTot // max(1, len(specs)),
        "horizon": horizon,
        "note": "명목 80% 밴드 held-out 피복. under-coverage<0.70 = 거짓확신(실패), over-coverage = 보수적(정직).",
    }

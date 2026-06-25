"""국면경로 forward — Hamilton 전이행렬 Markov 전진.

기존 cycles.regimeSwitching.hamiltonRegime 추정 전이행렬 P 를 재사용(추가 모델 0).
과거 smoothedProbs(회고)의 *미래* 대칭: π_h = π_0 · P^h → h개월 뒤 P(수축).
순수 함수(primitives 입력) — simulate.py 가 HamiltonResult 에서 추출해 호출.
"""

from __future__ import annotations

import numpy as np


def simulateRegimePath(p00: float, p11: float, currentProbs, horizon: int = 12, contractionIdx: int = 1) -> dict:
    """국면 forward Markov 경로.

    Args:
        p00: regime0(확장) 자기지속 확률.
        p11: regime1(수축) 자기지속 확률.
        currentProbs: 현재 평활확률 [P(확장), P(수축)] (smoothedProbs[-1]).
        horizon: 예측 개월.
        contractionIdx: 수축 regime 인덱스(기본 1).

    Returns:
        dict — forward([{h, pContraction}]) · current(현재 P(수축)) · ergodic(장기 P(수축)).
    """
    p = np.array([[p00, 1.0 - p00], [1.0 - p11, p11]])
    pi = np.asarray(currentProbs, dtype=float).reshape(2)
    pi = pi / pi.sum() if pi.sum() > 0 else np.array([0.5, 0.5])

    forward = []
    cur = pi.copy()
    for h in range(1, horizon + 1):
        cur = cur @ p
        forward.append({"h": h, "pContraction": round(float(cur[contractionIdx]), 4)})

    denom = 2.0 - p00 - p11
    ergodic = float((1.0 - p00) / denom) if denom > 1e-9 else float(pi[contractionIdx])
    return {
        "forward": forward,
        "current": round(float(pi[contractionIdx]), 4),
        "ergodic": round(ergodic, 4),
    }

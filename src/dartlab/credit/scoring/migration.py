"""Credit rating migration matrix → forward PD ladder.

L2 분석엔진 시간축 (등급 이력 → 현재 dCR → 미래 PD ladder).

학술 기반:
- CreditMetrics (J.P. Morgan, 1997) — Cohort 접근. 1-year transition matrix from
  observed rating changes, n-year forward 는 matrix power M^n.
- Basel III IRB — rating migration + cumulative default probability.
- dartlab 은 Cohort 채택. Hazard rate (continuous time, generator matrix log M)
  는 데이터 작을 때 불안정 — 79 개사 dCR 검증셋 규모에 부적합.

Standard ratings (dCR): AAA · AA+ · AA · AA- · A+ · A · A- · BBB+ · BBB · BBB- ·
BB+ · BB · BB- · B+ · B · B- · CCC · CC · C · D ('D' = 부도 absorbing state).

forecast precision = stable (observed transitions, 점예측 X). story 6 막 결합 시
'등급 이력 회고 → 현재 dCR → n 년 누적 PD' 형식으로 시간 narrative 직조.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from dartlab.credit.monitoring.history import _loadTransition

# dCR rating ordering (best → worst). 'dCR-D' 는 absorbing 부도 상태.
# credit.history._updateTransition 가 result['grade'] (= "dCR-AA" 풀 prefix 형식) 로
# 누적하므로 본 ordering 도 같은 형식 유지 — 실 transition.json 와 직접 매칭.
_DEFAULT_RATING_ORDER: tuple[str, ...] = (
    "dCR-AAA",
    "dCR-AA+",
    "dCR-AA",
    "dCR-AA-",
    "dCR-A+",
    "dCR-A",
    "dCR-A-",
    "dCR-BBB+",
    "dCR-BBB",
    "dCR-BBB-",
    "dCR-BB+",
    "dCR-BB",
    "dCR-BB-",
    "dCR-B+",
    "dCR-B",
    "dCR-B-",
    "dCR-CCC",
    "dCR-CC",
    "dCR-C",
    "dCR-D",
)
# absorbing 부도 라벨 — D 식별에 사용.
_DEFAULT_DEFAULT_LABEL = "dCR-D"


def _countsToMatrix(
    counts: dict[str, dict[str, int]],
    ratings: tuple[str, ...],
) -> np.ndarray:
    """관측 전이 횟수 → row-stochastic 전이 확률 matrix.

    빈 row (관측 0) → self-loop (대각 1, 안정 가정).
    'D' row → absorbing (D 행은 항상 self-loop only).
    """
    n = len(ratings)
    matrix = np.zeros((n, n))
    idx = {r: i for i, r in enumerate(ratings)}

    for fromR, toDict in counts.items():
        if fromR not in idx:
            continue
        i = idx[fromR]
        for toR, count in toDict.items():
            if toR not in idx:
                continue
            matrix[i, idx[toR]] += count

    for i in range(n):
        rowSum = matrix[i].sum()
        if rowSum > 0:
            matrix[i] /= rowSum
        else:
            matrix[i, i] = 1.0

    # absorbing 부도 식별 — full label ('dCR-D') 또는 short ('D') 둘 다 지원.
    default_idx = idx.get(_DEFAULT_DEFAULT_LABEL, idx.get("D"))
    if default_idx is not None:
        matrix[default_idx, :] = 0.0
        matrix[default_idx, default_idx] = 1.0

    return matrix


def buildTransitionMatrix(
    counts: dict[str, dict[str, int]] | None = None,
    *,
    ratings: tuple[str, ...] | None = None,
) -> pl.DataFrame:
    """등급 전이 확률 matrix (row-stochastic).

    Parameters
    ----------
    counts : dict | None
        ``{from_rating: {to_rating: count}}`` 형식의 관측 전이 횟수.
        None 이면 ``data/credit/transition.json`` 로드.
    ratings : tuple[str, ...] | None
        등급 순서 (best → worst). None 이면 dCR 기본 20 등급.

    Returns
    -------
    pl.DataFrame
        ``from_rating`` 컬럼 + 각 to_rating 별 확률 컬럼. 각 row sum ≈ 1.

    Notes
    -----
    빈 관측 row → self-loop (안정 가정). D row 는 absorbing.
    """
    if counts is None:
        counts = _loadTransition()
    if ratings is None:
        ratings = _DEFAULT_RATING_ORDER

    matrix = _countsToMatrix(counts, ratings)
    data: dict[str, list] = {"from_rating": list(ratings)}
    for j, toR in enumerate(ratings):
        data[toR] = [float(x) for x in matrix[:, j]]
    return pl.DataFrame(data)


def forwardPdLadder(
    counts: dict[str, dict[str, int]] | None = None,
    *,
    horizons: tuple[int, ...] = (1, 3, 5),
    ratings: tuple[str, ...] | None = None,
) -> pl.DataFrame:
    """등급별 누적 부도확률 ladder (Cohort matrix power).

    각 row 의 ``{h}yPD`` 컬럼 = ``M^h[rating, "D"]`` — h 년 누적 부도확률.
    horizon 증가 시 단조 증가, rating 악화 시 단조 증가가 정상.

    Parameters
    ----------
    counts : dict | None
        전이 횟수. None 이면 data/credit/transition.json 사용.
    horizons : tuple[int, ...]
        계산 horizon (년). 기본 (1, 3, 5).
    ratings : tuple[str, ...] | None
        등급 순서. None 이면 dCR 기본.

    Returns
    -------
    pl.DataFrame
        ``rating`` 컬럼 + horizon 별 PD 컬럼 (예: 1yPD, 3yPD, 5yPD).
        D 등급 미정의 시 모든 PD 가 0 (degenerate).
    """
    if counts is None:
        counts = _loadTransition()
    if ratings is None:
        ratings = _DEFAULT_RATING_ORDER

    matrix = _countsToMatrix(counts, ratings)
    idx = {r: i for i, r in enumerate(ratings)}

    # absorbing 부도 식별 — full label ('dCR-D') 또는 short ('D') 둘 다 지원.
    default_idx = idx.get(_DEFAULT_DEFAULT_LABEL, idx.get("D"))
    if default_idx is None:
        return pl.DataFrame(
            {
                "rating": list(ratings),
                **{f"{h}yPD": [0.0] * len(ratings) for h in horizons},
            }
        )

    out: dict[str, list] = {"rating": list(ratings)}
    for h in horizons:
        if h <= 0:
            out[f"{h}yPD"] = [0.0] * len(ratings)
            continue
        powered = np.linalg.matrix_power(matrix, h)
        out[f"{h}yPD"] = [float(x) for x in powered[:, default_idx]]
    return pl.DataFrame(out)

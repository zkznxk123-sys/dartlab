"""Triple Barrier Labeling — AFML Ch.3.2 (Lopez de Prado 2018).

3 경계: 수직 (시간 만료) / 상단 (익절 = +pt·σ) / 하단 (손절 = -sl·σ).

각 시점 t0 :
    upper = price[t0] · (1 + pt · vol)
    lower = price[t0] · (1 - sl · vol)
    horizon = t0 + vertical 일

먼저 닿은 경계로 라벨 :
    +1 : upper 닿음 (익절)
    -1 : lower 닿음 (손절)
     0 : 시간 만료 (sign(price[h] - price[t0]) 도 별도 기록)

dartlab 활용 :
    - Strategy DSL 의 entry signal 평가 라벨로 사용
    - Meta-labeling primary 모델 출력
    - calcStrategySnapshot 의 hit-rate 보다 학술적으로 정밀한 label
"""

from __future__ import annotations

import logging

import numpy as np

log = logging.getLogger(__name__)


def labelTripleBarrier(
    close: np.ndarray,
    *,
    pt: float = 2.0,
    sl: float = 1.0,
    vertical: int = 10,
    volWindow: int = 20,
) -> dict:
    """Triple Barrier 라벨링 — 종가 시계열에 대해 모든 진입 시점의 3경계 결과.

    Capabilities:
        - 일별 종가 array → 각 t0 의 label (+1/0/-1) + 도달 일수 + 실제 수익
        - 변동성 적응 (rolling std × pt/sl 로 경계 동적 결정)
        - AFML Ch.3 표준 — meta-labeling primary 모델 학습 라벨

    AIContext:
        - Sprint 3 ML 인프라 — strategy DSL 라벨 source
        - Triple Barrier 출력 → Meta-labeler (Logistic / RF) 입력

    Args:
        close: 종가 시계열 (1D numpy array, 양수). 길이 ≥ vertical + volWindow.
        pt: profit target multiplier on σ. 기본 ``2.0``.
        sl: stop loss multiplier on σ. 기본 ``1.0`` (asymmetric, 손절 좁게).
        vertical: 수직 경계 일수. 기본 ``10``.
        volWindow: rolling vol 추정 기간. 기본 ``20``.

    Returns:
        dict
            n : int — 라벨 개수 (= len(close) - vertical - volWindow)
            labels : np.ndarray — 각 t0 의 +1/0/-1
            holdDays : np.ndarray — 실제 hold 일수 (≤ vertical)
            returns : np.ndarray — 실제 log return at exit
            barriers : dict — {pt, sl, vertical, volWindow} 메타
            stats : dict — winRate / lossRate / timeoutRate / avgRet / avgHold
            interpretation : str

    Guide:
        AFML Ch.3 — pt/sl 비대칭 (2:1) + vertical 10 일 기본. ML primary 모델
        학습 라벨 SSOT.

    When:
        ML primary 모델 라벨 생성 + AI 백테스트 라벨링 답변.

    How:
        rolling vol 추정 → 각 t0 에서 pt×σ 상단/sl×σ 하단/vertical 일 3 경계 →
        가장 먼저 닿는 경계 label + hold + return.

    Requires:
        close ≥ vertical + volWindow + 1, 양수 종가.

    Raises:
        없음 — 데이터 부족 시 error 키.

    Example:
        >>> r = labelTripleBarrier(close, pt=2.0, sl=1.0, vertical=10)
        >>> r["stats"]["winRate"]
        0.45

    See Also:
        - calcCAR : event-study 누적 초과수익
        - vectorBacktest : 백테스트 본체
    """
    close = np.asarray(close, dtype=np.float64)
    n_raw = len(close)
    if n_raw < vertical + volWindow + 1:
        return {"error": "insufficient data"}

    # rolling log return + vol
    log_close = np.log(close)
    log_ret = np.diff(log_close)
    # vol[t] = std of log_ret[t-volWindow:t]
    n_lab = n_raw - vertical - volWindow
    if n_lab <= 0:
        return {"error": "insufficient data after barriers"}

    labels = np.zeros(n_lab, dtype=np.int8)
    hold_days = np.zeros(n_lab, dtype=np.int32)
    returns = np.zeros(n_lab, dtype=np.float64)

    for i in range(n_lab):
        t0 = i + volWindow
        # vol from i .. t0-1 of log_ret
        vol_window_data = log_ret[i:t0]
        if len(vol_window_data) < 5:
            continue
        sigma = float(np.std(vol_window_data, ddof=1))
        if sigma <= 0:
            continue
        p0 = close[t0]
        upper = p0 * (1 + pt * sigma)
        lower = p0 * (1 - sl * sigma)

        path = close[t0 + 1 : t0 + 1 + vertical]
        hit_label = 0
        hit_day = vertical
        hit_price = path[-1]
        for j, p in enumerate(path):
            if p >= upper:
                hit_label = 1
                hit_day = j + 1
                hit_price = p
                break
            if p <= lower:
                hit_label = -1
                hit_day = j + 1
                hit_price = p
                break
        labels[i] = hit_label
        hold_days[i] = hit_day
        returns[i] = float(np.log(hit_price / p0))

    win = int((labels == 1).sum())
    loss = int((labels == -1).sum())
    timeout = int((labels == 0).sum())
    total = max(win + loss + timeout, 1)
    avg_ret = float(returns.mean()) if len(returns) else 0.0
    avg_hold = float(hold_days.mean()) if len(hold_days) else 0.0

    return {
        "n": int(n_lab),
        "labels": labels,
        "holdDays": hold_days,
        "returns": returns,
        "barriers": {"pt": pt, "sl": sl, "vertical": vertical, "volWindow": volWindow},
        "stats": {
            "winRate": round(100 * win / total, 2),
            "lossRate": round(100 * loss / total, 2),
            "timeoutRate": round(100 * timeout / total, 2),
            "avgRet": round(avg_ret, 4),
            "avgHold": round(avg_hold, 1),
        },
        "interpretation": (
            f"{n_lab} 진입 시점, 익절 {round(100 * win / total, 1)}% / "
            f"손절 {round(100 * loss / total, 1)}% / "
            f"시간만료 {round(100 * timeout / total, 1)}%, "
            f"평균수익 {round(avg_ret * 100, 2)}%, 평균보유 {round(avg_hold, 1)}일."
        ),
    }


def metaLabel(
    primarySignals: np.ndarray,
    triBarrierLabels: np.ndarray,
) -> dict:
    """Meta-labeling — primary signal 의 정확도 (1) vs 오작동 (0) 라벨링.

    학술: AFML Ch.3.6 — primary 모델은 진입 방향 결정, secondary (meta) 모델은
    진입 size (확신도) 결정. precision-recall 트레이드오프 정밀 통제.

    Args:
        primarySignals: 1D ±1 진입 신호 (각 t0 의 long/short).
        triBarrierLabels: 같은 길이의 triple-barrier 라벨 (+1/0/-1).

    Returns:
        dict
            n : int
            metaLabels : np.ndarray — primary == barrier 면 1, 아니면 0
            precision : float — primary 신호 정확도 (%)
            agreementRate : float — 같은 부호 비율
            interpretation : str
    """
    p = np.asarray(primarySignals, dtype=np.int8)
    t = np.asarray(triBarrierLabels, dtype=np.int8)
    if len(p) != len(t):
        return {"error": "length mismatch"}
    # primary 신호가 0 인 행 제외
    mask = p != 0
    if mask.sum() == 0:
        return {"error": "no primary signals"}
    p_active = p[mask]
    t_active = t[mask]
    meta = (p_active == t_active).astype(np.int8)
    precision = float(meta.mean()) * 100
    return {
        "n": int(mask.sum()),
        "metaLabels": meta,
        "precision": round(precision, 2),
        "agreementRate": round(precision, 2),
        "interpretation": (
            f"primary {int(mask.sum())} 개 신호 중 정확 {round(precision, 1)}% — "
            "meta-labeler 가 이 정확도 위에서 size 결정."
        ),
    }

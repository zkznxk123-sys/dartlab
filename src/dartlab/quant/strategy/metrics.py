"""Strategy 평가 메트릭 — 표준 + Lopez de Prado overfitting guards.

외부 의존 0. numpy + math 만. 정규분포 CDF/PPF 는 자체 구현 (Abramowitz-Stegun).

학술 근거:
- Sharpe (1966) — Sharpe Ratio
- Sortino & van der Meer (1991) — Sortino Ratio
- Bailey & López de Prado (2014) — Deflated Sharpe Ratio (DSR)
- Bailey, Borwein, López de Prado, Zhu (2015) — Probability of Backtest Overfitting (PBO)
- López de Prado (2018) — AFML Combinatorial Purged Cross-Validation (CPCV)

SSOT: 메트릭 함수는 이 파일 한 곳. quant/_helpers.py 등에 중복 금지.
"""

from __future__ import annotations

import math
from itertools import combinations

import numpy as np

# 거래일 연환산 상수
TRADING_DAYS = 252


# ── 정규분포 자체 구현 (scipy 의존 0) ───────────────────────────────────────


def _norm_cdf(x: float) -> float:
    """표준정규 CDF (math.erf 기반)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_ppf(p: float) -> float:
    """표준정규 inverse CDF — Beasley-Springer-Moro 근사 (Acklam 2000)."""
    if p <= 0.0:
        return -float("inf")
    if p >= 1.0:
        return float("inf")
    a = [
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    ]
    b = [
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    ]
    d = [
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    ]
    plow = 0.02425
    phigh = 1 - plow
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1
        )
    if p <= phigh:
        q = p - 0.5
        r = q * q
        return (
            (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5])
            * q
            / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
        )
    q = math.sqrt(-2 * math.log(1 - p))
    return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
        (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1
    )


# ── 표준 메트릭 ─────────────────────────────────────────────────────────────


def sharpe(returns: np.ndarray, rf: float = 0.0) -> float:
    """연환산 Sharpe ratio. returns 는 일별 log return."""
    r = np.asarray(returns, dtype=np.float64)
    r = r[~np.isnan(r)]
    if len(r) < 2:
        return 0.0
    sd = float(np.std(r, ddof=1))
    if sd <= 0:
        return 0.0
    mu = float(np.mean(r)) - rf / TRADING_DAYS
    return float(mu / sd * np.sqrt(TRADING_DAYS))


def sortino(returns: np.ndarray, rf: float = 0.0) -> float:
    """Sortino ratio — 하방편차 기반."""
    r = np.asarray(returns, dtype=np.float64)
    r = r[~np.isnan(r)]
    if len(r) < 2:
        return 0.0
    downside = r[r < 0]
    if len(downside) == 0:
        return 0.0
    dd = float(np.std(downside, ddof=1))
    if dd <= 0:
        return 0.0
    mu = float(np.mean(r)) - rf / TRADING_DAYS
    return float(mu / dd * np.sqrt(TRADING_DAYS))


def mdd(equity: np.ndarray) -> float:
    """최대낙폭 (음수). equity 는 누적 자산 곡선."""
    e = np.asarray(equity, dtype=np.float64)
    e = e[~np.isnan(e)]
    if len(e) < 2:
        return 0.0
    peak = np.maximum.accumulate(e)
    dd = (e - peak) / peak
    return float(np.min(dd))


def winrate(trade_pnls: np.ndarray) -> float:
    """승률 — pnl > 0 비율."""
    p = np.asarray(trade_pnls, dtype=np.float64)
    if len(p) == 0:
        return 0.0
    return float(np.sum(p > 0) / len(p))


def profit_factor(trade_pnls: np.ndarray) -> float:
    """수익 / 손실 비율."""
    p = np.asarray(trade_pnls, dtype=np.float64)
    if len(p) == 0:
        return 0.0
    gains = float(np.sum(p[p > 0]))
    losses = -float(np.sum(p[p < 0]))
    if losses <= 0:
        return float("inf") if gains > 0 else 0.0
    return gains / losses


def expectancy(trade_pnls: np.ndarray) -> float:
    """1 거래당 기대수익."""
    p = np.asarray(trade_pnls, dtype=np.float64)
    if len(p) == 0:
        return 0.0
    return float(np.mean(p))


def turnover(positions: np.ndarray) -> float:
    """포지션 회전율 — 절대값 변화 합계."""
    p = np.asarray(positions, dtype=np.float64)
    if len(p) < 2:
        return 0.0
    return float(np.sum(np.abs(np.diff(p))))


def exposure(positions: np.ndarray) -> float:
    """포지션 유지 비율 — non-zero 비중."""
    p = np.asarray(positions, dtype=np.float64)
    if len(p) == 0:
        return 0.0
    return float(np.sum(np.abs(p) > 1e-9) / len(p))


# ── Overfitting Guards ──────────────────────────────────────────────────────


def dsr(observed_sharpe: float, returns: np.ndarray, n_trials: int = 1) -> float:
    """Deflated Sharpe Ratio (Bailey-López de Prado 2014).

    백테스트 시도 횟수(n_trials) 와 returns 의 skewness/kurtosis 를 정정해서
    "이 Sharpe 가 우연이 아닐 확률" 을 [0, 1] 로 반환.

    DSR > 0.95 → 통계적으로 강함, DSR < 0.5 → 의심.

    Args:
        observed_sharpe: 관측 Sharpe (연환산)
        returns: 일별 수익률 (skew/kurtosis 계산용)
        n_trials: 다중 백테스트 시도 횟수 (1 이면 정정 약함)

    Returns:
        DSR ∈ [0, 1]
    """
    r = np.asarray(returns, dtype=np.float64)
    r = r[~np.isnan(r)]
    T = len(r)
    if T < 30:
        return 0.0
    # skewness/kurtosis (excess)
    mu = float(np.mean(r))
    sd = float(np.std(r, ddof=1))
    if sd <= 0:
        return 0.0
    z = (r - mu) / sd
    skew = float(np.mean(z**3))
    kurt = float(np.mean(z**4) - 3.0)
    # SR (일별)
    sr = observed_sharpe / np.sqrt(TRADING_DAYS)
    # 기대 max Sharpe under null (Bailey-Lopez)
    em = np.euler_gamma
    if n_trials < 2:
        sr0 = 0.0
    else:
        z1 = _norm_ppf(1 - 1.0 / n_trials)
        z2 = _norm_ppf(1 - 1.0 / (n_trials * math.e))
        sr0 = (1 - em) * z1 + em * z2
        sr0 /= np.sqrt(TRADING_DAYS)
    # SR 의 표준오차 (정정 — 정규성 위반)
    var_sr = (1 - skew * sr + (kurt / 4.0) * sr**2) / (T - 1)
    if var_sr <= 0:
        return 0.0
    z_dsr = (sr - sr0) / np.sqrt(var_sr)
    return float(_norm_cdf(z_dsr))


def pbo(in_sample: np.ndarray, out_of_sample: np.ndarray) -> float:
    """Probability of Backtest Overfitting (Bailey-Borwein-López de Prado-Zhu 2015).

    in-sample 에서 최고 성과를 낸 전략이 out-of-sample 에서 중간값 이하일 확률.
    PBO > 0.5 → 과적합 의심.

    Args:
        in_sample: shape (n_trials, n_segments) — 각 trial × split 의 IS Sharpe
        out_of_sample: shape (n_trials, n_segments) — 동일 trial 의 OOS Sharpe

    Returns:
        PBO ∈ [0, 1]
    """
    is_arr = np.asarray(in_sample, dtype=np.float64)
    oos_arr = np.asarray(out_of_sample, dtype=np.float64)
    if is_arr.ndim != 2 or oos_arr.ndim != 2 or is_arr.shape != oos_arr.shape:
        return 0.0
    n_trials, n_segments = is_arr.shape
    if n_segments < 2:
        return 0.0
    overfit_count = 0
    for s in range(n_segments):
        best_trial = int(np.argmax(is_arr[:, s]))
        oos_rank = float(np.sum(oos_arr[:, s] >= oos_arr[best_trial, s])) / n_trials
        if oos_rank > 0.5:
            overfit_count += 1
    return float(overfit_count / n_segments)


# ── CPCV split 생성 (Lopez AFML) ────────────────────────────────────────────


def cpcv_splits(n_obs: int, n_splits: int = 6, n_test: int = 2, embargo: int = 0):
    """Combinatorial Purged Cross-Validation 인덱스 분할.

    n_splits 그룹으로 나누고, n_test 개 그룹을 test 로 선택하는 모든 조합.
    train 은 test 와 인접한 embargo 만큼 purge.

    Args:
        n_obs: 시계열 길이
        n_splits: 전체 분할 수
        n_test: test 그룹 수 (n_splits choose n_test 만큼 split 생성)
        embargo: test 양 끝에서 purge 할 관측치 수

    Yields:
        (train_idx, test_idx) tuples
    """
    if n_obs < n_splits * 2:
        return
    bins = np.array_split(np.arange(n_obs), n_splits)
    for combo in combinations(range(n_splits), n_test):
        test_groups = [bins[i] for i in combo]
        test_idx = np.concatenate(test_groups)
        # purge: test 양 끝에 embargo
        purged = set(test_idx.tolist())
        for tg in test_groups:
            lo = max(0, tg[0] - embargo)
            hi = min(n_obs, tg[-1] + 1 + embargo)
            for k in range(lo, hi):
                purged.add(k)
        train_idx = np.array([i for i in range(n_obs) if i not in purged], dtype=np.int64)
        yield train_idx, test_idx

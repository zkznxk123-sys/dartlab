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
    """연환산 Sharpe ratio.

    Parameters
    ----------
    returns : np.ndarray
        일별 log return 시계열.
    rf : float
        연간 무위험 이자율. 기본 0.

    Returns
    -------
    float
        연환산 Sharpe ratio (배). 표본 < 2 또는 std=0 이면 0.0.
    """
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
    """Sortino ratio — 하방편차 기반.

    Parameters
    ----------
    returns : np.ndarray
        일별 log return 시계열.
    rf : float
        연간 무위험 이자율. 기본 0.

    Returns
    -------
    float
        연환산 Sortino ratio (배). 하방 수익률 없거나 std=0 이면 0.0.
    """
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
    """최대낙폭 (Maximum Drawdown).

    Parameters
    ----------
    equity : np.ndarray
        누적 자산 곡선 (예: 초기 1.0 부터).

    Returns
    -------
    float
        최대낙폭 비율 (음수, %). 예: -0.25 = -25% 낙폭. 표본 < 2 이면 0.0.
    """
    e = np.asarray(equity, dtype=np.float64)
    e = e[~np.isnan(e)]
    if len(e) < 2:
        return 0.0
    peak = np.maximum.accumulate(e)
    dd = (e - peak) / peak
    return float(np.min(dd))


def winrate(trade_pnls: np.ndarray) -> float:
    """승률 — pnl > 0 비율.

    Parameters
    ----------
    trade_pnls : np.ndarray
        거래별 손익 배열.

    Returns
    -------
    float
        승률 (비율, 0~1). 거래 없으면 0.0.
    """
    p = np.asarray(trade_pnls, dtype=np.float64)
    if len(p) == 0:
        return 0.0
    return float(np.sum(p > 0) / len(p))


def profitFactor(trade_pnls: np.ndarray) -> float:
    """총 수익 / 총 손실 비율.

    Parameters
    ----------
    trade_pnls : np.ndarray
        거래별 손익 배열.

    Returns
    -------
    float
        Profit Factor (배). 손실 0 이면 inf (수익 있을 때) 또는 0.0.
    """
    p = np.asarray(trade_pnls, dtype=np.float64)
    if len(p) == 0:
        return 0.0
    gains = float(np.sum(p[p > 0]))
    losses = -float(np.sum(p[p < 0]))
    if losses <= 0:
        return float("inf") if gains > 0 else 0.0
    return gains / losses


def expectancy(trade_pnls: np.ndarray) -> float:
    """1 거래당 기대수익.

    Parameters
    ----------
    trade_pnls : np.ndarray
        거래별 손익 배열.

    Returns
    -------
    float
        거래당 평균 손익 (원). 거래 없으면 0.0.
    """
    p = np.asarray(trade_pnls, dtype=np.float64)
    if len(p) == 0:
        return 0.0
    return float(np.mean(p))


def turnover(positions: np.ndarray) -> float:
    """포지션 회전율 — 절대값 변화 합계.

    Parameters
    ----------
    positions : np.ndarray
        시점별 포지션 크기 배열.

    Returns
    -------
    float
        총 회전 (절대값 변화 합, 배). 표본 < 2 이면 0.0.
    """
    p = np.asarray(positions, dtype=np.float64)
    if len(p) < 2:
        return 0.0
    return float(np.sum(np.abs(np.diff(p))))


def exposure(positions: np.ndarray) -> float:
    """포지션 유지 비율 — non-zero 비중.

    Parameters
    ----------
    positions : np.ndarray
        시점별 포지션 크기 배열.

    Returns
    -------
    float
        포지션 유지 비율 (0~1). 포지션 없으면 0.0.
    """
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


def cpcvSplits(n_obs: int, n_splits: int = 6, n_test: int = 2, embargo: int = 0):
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


# ══════════════════════════════════════════════════════════════════════
# Grinold & Kahn "Active Portfolio Management" Ch.5-8 메트릭
# ══════════════════════════════════════════════════════════════════════
#
# IC (Information Coefficient), IR (Information Ratio), Fundamental Law
# (IR = IC × √breadth), IC significance (t-stat), factor decay (AR(1)),
# breadth 자동 추정 — 모두 numpy 순수 구현. scipy 의존 0.
#
# 학술 근거:
# - Grinold, R. & Kahn, R. (2000). Active Portfolio Management 2nd ed.
#   Ch.5 "Residual Risk and Return: The Information Ratio"
#   Ch.6 "The Fundamental Law of Active Management"
#   Ch.8 "Information Analysis"
#
# SSOT 원칙: quant 메트릭 전부 이 파일 한 곳.


def pearsonCorr(x: np.ndarray, y: np.ndarray) -> float:
    """Pearson 선형상관계수 — NaN 쌍 제거 후 계산.

    Returns
    -------
    float
        ρ ∈ [-1, 1]. 표본 < 2 또는 분산 0 이면 NaN/0.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = ~(np.isnan(x) | np.isnan(y))
    x, y = x[mask], y[mask]
    if x.size < 2:
        return float("nan")
    xc = x - x.mean()
    yc = y - y.mean()
    denom = np.sqrt((xc * xc).sum() * (yc * yc).sum())
    if denom == 0.0:
        return 0.0
    return float((xc * yc).sum() / denom)


def _avgRank(a: np.ndarray) -> np.ndarray:
    """평균 rank. 동률 → 해당 위치 rank 들의 평균으로 대체."""
    order = np.argsort(a, kind="mergesort")
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(a) + 1, dtype=float)
    sorted_a = a[order]
    i = 0
    n = len(a)
    while i < n:
        j = i
        while j + 1 < n and sorted_a[j + 1] == sorted_a[i]:
            j += 1
        if j > i:
            avg = (ranks[order[i : j + 1]]).mean()
            ranks[order[i : j + 1]] = avg
        i = j + 1
    return ranks


def spearmanCorr(x: np.ndarray, y: np.ndarray) -> float:
    """Spearman 순위상관계수 — 동률 평균 rank 처리.

    Parameters
    ----------
    x : np.ndarray
        첫 번째 변수 배열.
    y : np.ndarray
        두 번째 변수 배열 (x 와 같은 길이).

    Returns
    -------
    float
        ρ_s ∈ [-1, 1]. 표본 < 2 이면 NaN.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = ~(np.isnan(x) | np.isnan(y))
    x, y = x[mask], y[mask]
    if x.size < 2:
        return float("nan")
    return pearsonCorr(_avgRank(x), _avgRank(y))


def calcIR(alphaSeries: np.ndarray) -> float:
    """Information Ratio = mean(alpha) / std(alpha). 연환산은 호출자 책임.

    Grinold Ch.5 의 raw IR. std 는 표본표준편차 (ddof=1).
    """
    a = np.asarray(alphaSeries, dtype=float)
    a = a[~np.isnan(a)]
    if a.size < 2:
        return float("nan")
    s = a.std(ddof=1)
    if s == 0.0:
        return 0.0
    return float(a.mean() / s)


def fundamentalLawIR(ic: float, breadth: int) -> float:
    """Fundamental Law of Active Management (Grinold Ch.6): IR = IC × √breadth.

    breadth = 연간 상호 독립인 베팅 수.
    예) IC=0.05, breadth=400 → IR=1.0 (Grinold 대표 사례).
    """
    if breadth < 1:
        return 0.0
    return float(ic * np.sqrt(breadth))


def rollingTimeSeriesZscore(series: np.ndarray, window: int) -> np.ndarray:
    """Rolling z-score (Grinold Ch.3 팩터 정규화): z_t = (x_t − μ_w) / σ_w.

    첫 window-1 개는 NaN. std=0 또는 표본<2 이면 NaN.
    """
    s = np.asarray(series, dtype=float)
    n = s.size
    out = np.full(n, np.nan, dtype=float)
    if window < 2 or n < window:
        return out
    for i in range(window - 1, n):
        chunk = s[i - window + 1 : i + 1]
        chunk = chunk[~np.isnan(chunk)]
        if chunk.size < 2:
            continue
        sd = chunk.std(ddof=1)
        if sd == 0.0:
            continue
        out[i] = (s[i] - chunk.mean()) / sd
    return out


def icSignificance(icSeries: np.ndarray, *, nStocks: int | None = None) -> dict:
    """IC 시계열의 통계적 유의성 (Grinold Ch.8).

    t = mean(IC) / (std(IC) / √T). |t| > 2 → 유의.
    """
    r = np.asarray(icSeries, dtype=float)
    r = r[~np.isnan(r)]
    T = r.size
    if T < 2:
        return {
            "meanIC": float("nan"),
            "stdIC": float("nan"),
            "tStat": None,
            "hitRate": float("nan"),
            "ci95": (float("nan"), float("nan")),
            "isSignificant": False,
            "nPeriods": T,
            "nStocks": nStocks,
        }
    mu = float(r.mean())
    sd = float(r.std(ddof=1))
    se = sd / np.sqrt(T) if T > 0 else float("nan")
    t_stat = float(mu / se) if se > 0 else 0.0
    hit = float(np.mean(np.sign(r) == np.sign(mu))) if mu != 0 else 0.5
    return {
        "meanIC": mu,
        "stdIC": sd,
        "tStat": t_stat,
        "hitRate": hit,
        "ci95": (float(mu - 1.96 * se), float(mu + 1.96 * se)),
        "isSignificant": abs(t_stat) > 2.0,
        "nPeriods": T,
        "nStocks": nStocks,
    }


def factorDecayRate(icSeries: np.ndarray) -> dict:
    """IC 시계열 AR(1) 자기상관 → 정보 반감기.

    half_life = ln(0.5) / ln(ρ)  (ρ > 0).
    """
    r = np.asarray(icSeries, dtype=float)
    r = r[~np.isnan(r)]
    if r.size < 4:
        return {"autocorr": None, "halfLifePeriods": None, "persistence": "none"}
    a = r[:-1] - r[:-1].mean()
    b = r[1:] - r[1:].mean()
    denom = np.sqrt((a * a).sum() * (b * b).sum())
    if denom == 0:
        return {"autocorr": 0.0, "halfLifePeriods": None, "persistence": "none"}
    rho = float((a * b).sum() / denom)
    half_life = float(np.log(0.5) / np.log(rho)) if rho > 0.01 else None
    if rho > 0.5:
        persistence = "high"
    elif rho > 0.2:
        persistence = "medium"
    elif rho > 0.0:
        persistence = "low"
    else:
        persistence = "none"
    return {"autocorr": rho, "halfLifePeriods": half_life, "persistence": persistence}


def breadthFromFrequency(
    *,
    rebalancesPerYear: int,
    nStocks: int,
    independenceRatio: float = 1.0,
) -> int:
    """Grinold Fundamental Law 의 breadth (N) 자동 추정.

    breadth ≈ rebalancesPerYear × nStocks × independenceRatio.
    """
    if rebalancesPerYear < 1 or nStocks < 1:
        return 0
    ratio = max(0.0, min(1.0, float(independenceRatio)))
    return int(rebalancesPerYear * nStocks * ratio)


def impliedIRFromICDistribution(icSeries: np.ndarray, breadth: int) -> dict:
    """IC 분포 + breadth → 이론 IR vs 실현 ICIR 비교.

    Fundamental Law (IR = IC × √breadth) 이론값과 실현 ICIR 을 비교해
    전략 효율성을 평가한다.

    Parameters
    ----------
    icSeries : np.ndarray
        IC 시계열 (각 기간의 횡단면 IC).
    breadth : int
        연간 독립 베팅 수 (Grinold Fundamental Law 정의).

    Returns
    -------
    dict
        meanIC : float — 평균 IC (비율)
        theoreticalIR : float — 이론 IR = meanIC × √breadth (배)
        realizedICIR : float — 실현 ICIR = meanIC / stdIC (배)
        efficiency : float — realizedICIR / theoreticalIR (비율)
    """
    r = np.asarray(icSeries, dtype=float)
    r = r[~np.isnan(r)]
    if r.size < 2:
        return {
            "meanIC": float("nan"),
            "theoreticalIR": float("nan"),
            "realizedICIR": float("nan"),
            "efficiency": float("nan"),
        }
    mu = float(r.mean())
    sd = float(r.std(ddof=1))
    theo_ir = float(mu * np.sqrt(max(breadth, 0)))
    real_icir = float(mu / sd) if sd > 0 else 0.0
    eff = float(real_icir / theo_ir) if theo_ir != 0 else float("nan")
    return {
        "meanIC": mu,
        "theoreticalIR": theo_ir,
        "realizedICIR": real_icir,
        "efficiency": eff,
    }


# ── Deprecated snake_case aliases ────────────────────────
from dartlab.quant._helpers import _deprecatedAlias as _dep

profit_factor = _dep(profitFactor, "profit_factor")
cpcv_splits = _dep(cpcvSplits, "cpcv_splits")

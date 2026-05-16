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


def _normCdf(x: float) -> float:
    """표준정규 CDF (math.erf 기반)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _normPpf(p: float) -> float:
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

    Capabilities:
        일별 수익률 → (mean - rf/252) / std × √252 연환산 Sharpe. Sharpe (1966)
        risk-adjusted return 표준.

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

    Example:
        >>> sharpe(returns)
        1.45

    Guide:
        > 1.0 = 양호, > 2.0 = 우수, < 0 = 무위험 미달. DSR + haircutSharpe 와 함께
        다중 검정 보정 권장.

    When:
        백테스트 metrics + AI 전략 평가 진입점.

    How:
        ddof=1 std + 252 거래일 가정. log return 입력 가정.

    Requires:
        returns ≥ 2 + std > 0.

    Raises:
        없음 — 0.0 반환.

    See Also:
        - sortino : 하방편차 기반
        - dsr : 다중 시도 정정

    AIContext:
        Sharpe 단독 인용 + sample 길이/n_trials 누락 금지 — dsr 동반.
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

    Capabilities:
        일별 수익률 → (mean - rf/252) / downsideStd × √252. Sharpe 대비 상방
        변동성 (좋은 변동) 보정 제외.

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

    Example:
        >>> sortino(returns)
        2.10

    Guide:
        Sharpe < Sortino = 상방 변동성 큰 자산 (성장주). 펀드 평가 시 Sortino 우선.

    When:
        백테스트 metrics + AI 비대칭 risk 답변.

    How:
        downside = r[r<0] → ddof=1 std → 연환산.

    Requires:
        returns ≥ 2 + 하방 수익률 ≥ 1.

    Raises:
        없음.

    See Also:
        - sharpe : 양방향 변동

    AIContext:
        Sharpe vs Sortino 차이 인용으로 비대칭성 평가.
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

    Capabilities:
        누적 자산 곡선 → cumulative peak 대비 최대 낙폭 (음수). Calmar 비율의
        분모 + 매크로 리스크 표준.

    Parameters
    ----------
    equity : np.ndarray
        누적 자산 곡선 (예: 초기 1.0 부터).

    Returns
    -------
    float
        최대낙폭 비율 (음수, %). 예: -0.25 = -25% 낙폭. 표본 < 2 이면 0.0.

    Example:
        >>> mdd(np.array([1.0, 1.1, 0.9, 0.95]))
        -0.182

    Guide:
        |mdd| > 0.5 = 회복 어려움. 시점 (Drawdown date) 함께 인용해 macro
        이벤트 연결.

    When:
        백테스트 metrics + AI 낙폭 답변.

    How:
        cumulative max → (equity - peak) / peak → min.

    Requires:
        equity ≥ 2.

    Raises:
        없음.

    See Also:
        - calcTailrisk : VaR/CVaR 동반

    AIContext:
        mdd 값 + 시점 함께 인용 (macro 이벤트 매핑).
    """
    e = np.asarray(equity, dtype=np.float64)
    e = e[~np.isnan(e)]
    if len(e) < 2:
        return 0.0
    peak = np.maximum.accumulate(e)
    dd = (e - peak) / peak
    return float(np.min(dd))


def winrate(tradePnls: np.ndarray) -> float:
    """승률 — pnl > 0 비율.

    Capabilities:
        거래별 손익 → 양수 비율. 트레이딩 평가 표준 metric.

    Parameters
    ----------
    tradePnls : np.ndarray
        거래별 손익 배열.

    Returns
    -------
    float
        승률 (비율, 0~1). 거래 없으면 0.0.

    Example:
        >>> winrate(np.array([1, -1, 2, -0.5]))
        0.5

    Guide:
        winrate 50% 미만이어도 profitFactor 큰 전략 흑자 가능 — 둘 함께 인용.

    When:
        백테스트 metrics + AI 전략 승률 답변.

    How:
        sum(p > 0) / n.

    Requires:
        tradePnls 비어있지 않음.

    Raises:
        없음.

    See Also:
        - profitFactor : 총 수익/손실 비율
        - expectancy : 거래당 평균

    AIContext:
        winrate < 50% + PF > 1.5 → 비대칭 양봉 전략.
    """
    p = np.asarray(tradePnls, dtype=np.float64)
    if len(p) == 0:
        return 0.0
    return float(np.sum(p > 0) / len(p))


def profitFactor(tradePnls: np.ndarray) -> float:
    """총 수익 / 총 손실 비율.

    Capabilities:
        승 거래 합 / 손 거래 합 (절댓값). 1.5+ = 양호, 2.0+ = 우수.

    Parameters
    ----------
    tradePnls : np.ndarray
        거래별 손익 배열.

    Returns
    -------
    float
        Profit Factor (배). 손실 0 이면 inf (수익 있을 때) 또는 0.0.

    Example:
        >>> profitFactor(np.array([3, -1, 2, -1]))
        2.5

    Guide:
        winrate × avgWin / avgLoss = PF. PF 1.0 = breakeven (수수료 차감 후 손실).

    When:
        백테스트 metrics + AI 전략 비율 답변.

    How:
        sum(p>0) / |sum(p<0)|.

    Requires:
        tradePnls 비어있지 않음.

    Raises:
        없음 — 손실 0 + 수익 0 → 0.0.

    See Also:
        - winrate : 승률
        - expectancy : 거래당 평균

    AIContext:
        PF + winrate 인용으로 양봉/음봉 비율 답변.
    """
    p = np.asarray(tradePnls, dtype=np.float64)
    if len(p) == 0:
        return 0.0
    gains = float(np.sum(p[p > 0]))
    losses = -float(np.sum(p[p < 0]))
    if losses <= 0:
        return float("inf") if gains > 0 else 0.0
    return gains / losses


def expectancy(tradePnls: np.ndarray) -> float:
    """1 거래당 기대수익.

    Capabilities:
        거래별 손익 평균. 양수 = 흑자 전략, 음수 = 적자.

    Parameters
    ----------
    tradePnls : np.ndarray
        거래별 손익 배열.

    Returns
    -------
    float
        거래당 평균 손익 (원). 거래 없으면 0.0.

    Example:
        >>> expectancy(np.array([1, -1, 2, -0.5]))
        0.375

    Guide:
        expectancy × 거래 빈도 = 연간 기대 수익. 수수료 차감 후 인용.

    When:
        백테스트 metrics + AI 거래당 기대값 답변.

    How:
        mean(p).

    Requires:
        tradePnls 비어있지 않음.

    Raises:
        없음.

    See Also:
        - profitFactor : 총합 비율
        - sharpe : 위험 조정

    AIContext:
        expectancy × 빈도 = 연간 기대 수익, 수수료 차감 후 인용.
    """
    p = np.asarray(tradePnls, dtype=np.float64)
    if len(p) == 0:
        return 0.0
    return float(np.mean(p))


def turnover(positions: np.ndarray) -> float:
    """포지션 회전율 — 절대값 변화 합계.

    Capabilities:
        포지션 시계열 절대값 차분 합 → 매매 빈도. 거래비용 추정 + 전략 활성도.

    Parameters
    ----------
    positions : np.ndarray
        시점별 포지션 크기 배열.

    Returns
    -------
    float
        총 회전 (절대값 변화 합, 배). 표본 < 2 이면 0.0.

    Example:
        >>> turnover(np.array([0, 1, 0, 1]))
        3.0

    Guide:
        연간 turnover × spread/2 = 대략 transaction cost. 1000% / 년 = 일평균 4%
        회전 (highfreq).

    When:
        백테스트 비용 추정 + AI 전략 빈도 답변.

    How:
        sum(|diff(positions)|).

    Requires:
        positions ≥ 2.

    Raises:
        없음.

    See Also:
        - exposure : 포지션 유지 비율

    AIContext:
        turnover × spread = 대략 거래비용 추정.
    """
    p = np.asarray(positions, dtype=np.float64)
    if len(p) < 2:
        return 0.0
    return float(np.sum(np.abs(np.diff(p))))


def exposure(positions: np.ndarray) -> float:
    """포지션 유지 비율 — non-zero 비중.

    Capabilities:
        포지션 시계열에서 |p| > 0 시점 비율. 시장 노출 정량화.

    Parameters
    ----------
    positions : np.ndarray
        시점별 포지션 크기 배열.

    Returns
    -------
    float
        포지션 유지 비율 (0~1). 포지션 없으면 0.0.

    Example:
        >>> exposure(np.array([0, 1, 0, 1]))
        0.5

    Guide:
        exposure 1.0 = 항상 시장 노출 (buy & hold). 0.3 = 70% 캐쉬 보유.
        annualReturn 인용 시 exposure 보정.

    When:
        백테스트 + AI 시장 노출 답변.

    How:
        sum(|p| > 1e-9) / n.

    Requires:
        positions 비어있지 않음.

    Raises:
        없음.

    See Also:
        - turnover : 변화량

    AIContext:
        exposure 보정 후 annualReturn 인용 (캐쉬 보유 기간 반영).
    """
    p = np.asarray(positions, dtype=np.float64)
    if len(p) == 0:
        return 0.0
    return float(np.sum(np.abs(p) > 1e-9) / len(p))


# ── Overfitting Guards ──────────────────────────────────────────────────────


def dsr(observedSharpe: float, returns: np.ndarray, nTrials: int = 1) -> float:
    """Deflated Sharpe Ratio (Bailey-López de Prado 2014).

    Capabilities:
        백테스트 시도 횟수(n_trials) 와 returns 의 skewness/kurtosis 를 정정해서
        "이 Sharpe 가 우연이 아닐 확률" 을 [0, 1] 로 반환. DSR > 0.95 → 통계적
        강함, < 0.5 → 의심.

    Args:
        observedSharpe: 관측 Sharpe (연환산)
        returns: 일별 수익률 (skew/kurtosis 계산용)
        nTrials: 다중 백테스트 시도 횟수 (1 이면 정정 약함)

    Returns:
        DSR ∈ [0, 1]

    Example:
        >>> dsr(1.5, returns, nTrials=10)
        0.78

    Guide:
        Bailey-Lopez 2014 SR* 와 결합. n_trials 100+ 면 통계적 압박 큼. 본 함수
        는 within-strategy DSR — between-strategy 는 haircutSharpe.

    When:
        백테스트 거버넌스 + AI 전략 진정성 답변.

    How:
        skewness/kurtosis 정정 후 SR variance → null 기대 max SR (Euler) →
        z-stat → CDF.

    Requires:
        returns ≥ 30 + observedSharpe 연환산.

    Raises:
        없음.

    See Also:
        - haircutSharpe : between-strategy 보정
        - pbo : 과적합 확률

    AIContext:
        DSR + Sharpe 동시 인용 — 단순 Sharpe 만으로 진정성 단정 금지.
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
    sr = observedSharpe / np.sqrt(TRADING_DAYS)
    # 기대 max Sharpe under null (Bailey-Lopez)
    em = np.euler_gamma
    if nTrials < 2:
        sr0 = 0.0
    else:
        z1 = _normPpf(1 - 1.0 / nTrials)
        z2 = _normPpf(1 - 1.0 / (nTrials * math.e))
        sr0 = (1 - em) * z1 + em * z2
        sr0 /= np.sqrt(TRADING_DAYS)
    # SR 의 표준오차 (정정 — 정규성 위반)
    var_sr = (1 - skew * sr + (kurt / 4.0) * sr**2) / (T - 1)
    if var_sr <= 0:
        return 0.0
    z_dsr = (sr - sr0) / np.sqrt(var_sr)
    return float(_normCdf(z_dsr))


def pbo(inSample: np.ndarray, outOfSample: np.ndarray) -> float:
    """Probability of Backtest Overfitting (Bailey-Borwein-López de Prado-Zhu 2015).

    Capabilities:
        in-sample 에서 최고 성과 전략이 out-of-sample 중간값 이하일 확률. PBO >
        0.5 = 과적합. CSCV 기반.

    Args:
        inSample: shape (n_trials, n_segments) — 각 trial × split 의 IS Sharpe
        outOfSample: shape (n_trials, n_segments) — 동일 trial 의 OOS Sharpe

    Returns:
        PBO ∈ [0, 1]

    Example:
        >>> pbo(is_arr, oos_arr)
        0.35

    Guide:
        PBO < 0.3 = 강건. > 0.5 = 강한 과적합. cpcvSplits + 본 함수 결합 표준.

    When:
        백테스트 거버넌스 + AI 과적합 답변.

    How:
        각 segment 에서 IS argmax → OOS rank → 중간값 이하 카운트 / segment 수.

    Requires:
        inSample/outOfSample 동일 shape (≥ 2 segment).

    Raises:
        없음 — 0.0 반환.

    See Also:
        - dsr : DSR 단일 정정
        - cpcvSplits : 분할 생성

    AIContext:
        DSR + PBO 동시 인용 — 과적합 양면 진단.
    """
    is_arr = np.asarray(inSample, dtype=np.float64)
    oos_arr = np.asarray(outOfSample, dtype=np.float64)
    if is_arr.ndim != 2 or oos_arr.ndim != 2 or is_arr.shape != oos_arr.shape:
        return 0.0
    nTrials, n_segments = is_arr.shape
    if n_segments < 2:
        return 0.0
    overfit_count = 0
    for s in range(n_segments):
        best_trial = int(np.argmax(is_arr[:, s]))
        oos_rank = float(np.sum(oos_arr[:, s] >= oos_arr[best_trial, s])) / nTrials
        if oos_rank > 0.5:
            overfit_count += 1
    return float(overfit_count / n_segments)


# ── CPCV split 생성 (Lopez AFML) ────────────────────────────────────────────


def cpcvSplits(nObs: int, nSplits: int = 6, nTest: int = 2, embargo: int = 0) -> list[tuple]:
    """Combinatorial Purged Cross-Validation 인덱스 분할.

    Capabilities:
        Lopez de Prado AFML Ch.12 CPCV — n_splits choose n_test 조합 + embargo
        purge. pbo + DSR 의 base.

    Args:
        nObs: 시계열 길이
        nSplits: 전체 분할 수
        nTest: test 그룹 수 (nSplits choose nTest 만큼 split 생성)
        embargo: test 양 끝에서 purge 할 관측치 수

    Yields:
        (train_idx, test_idx) tuples

    Example:
        >>> list(cpcvSplits(100, nSplits=6, nTest=2))[:1]

    Guide:
        nSplits 6 + nTest 2 → 15 split (C(6,2)). embargo 는 1 일 거래 다음 영향
        제거.

    When:
        백테스트 CV 분할 + pbo 입력 생성.

    How:
        np.array_split → combinations(C(n,k)) → embargo purge → train_idx 생성.

    Requires:
        nObs ≥ nSplits × 2.

    Raises:
        없음 — 부족 시 empty yield.

    See Also:
        - pbo : 본 함수 결과 소비
        - dsr : 단일 정정

    AIContext:
        CPCV + pbo + DSR 3 종 결합으로 과적합 회피 표준 protocol.
    """
    if nObs < nSplits * 2:
        return
    bins = np.array_split(np.arange(nObs), nSplits)
    for combo in combinations(range(nSplits), nTest):
        test_groups = [bins[i] for i in combo]
        test_idx = np.concatenate(test_groups)
        # purge: test 양 끝에 embargo
        purged = set(test_idx.tolist())
        for tg in test_groups:
            lo = max(0, tg[0] - embargo)
            hi = min(nObs, tg[-1] + 1 + embargo)
            for k in range(lo, hi):
                purged.add(k)
        train_idx = np.array([i for i in range(nObs) if i not in purged], dtype=np.int64)
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

    Capabilities:
        선형 관계 강도 측정. -1 (역상관) ~ +1 (정상관). 변수간 상관/팩터 IC
        보조.

    Returns
    -------
    float
        ρ ∈ [-1, 1]. 표본 < 2 또는 분산 0 이면 NaN/0.

    Example:
        >>> pearsonCorr(x, y)
        0.42

    Guide:
        outlier 민감 — 큰 outlier 시 Spearman 대체 권장. |ρ| > 0.7 = 강한 선형.

    When:
        팩터 분석 + AI 변수 상관 답변.

    How:
        NaN mask → centered xy → 분자/분모.

    Requires:
        x/y 같은 길이 + 표본 ≥ 2.

    Raises:
        없음 — NaN/0 반환.

    See Also:
        - spearmanCorr : rank-based
        - calcFactorIC : Spearman IC

    AIContext:
        Pearson + Spearman 동시 비교 시 비선형 신호 검출.
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

    Capabilities:
        rank-based 상관 — outlier robust. 팩터 IC 표준 (Alphalens).

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

    Example:
        >>> spearmanCorr(x, y)
        0.55

    Guide:
        Pearson 보다 outlier robust. |ρ_s| > 0.5 = 강한 단조 관계. 팩터 IC 본
        함수 권장.

    When:
        팩터 IC + AI 비선형 관계 답변.

    How:
        avg rank (동률 평균) → Pearson on ranks.

    Requires:
        x/y 같은 길이 + 표본 ≥ 2.

    Raises:
        없음 — NaN 반환.

    See Also:
        - pearsonCorr : 선형
        - calcFactorIC : IC 시계열

    AIContext:
        Spearman 단독 인용 + 표본 크기 (n) 함께.
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

    Capabilities:
        Grinold Ch.5 raw IR — alpha 시리즈 mean/std 비율. Active 운용의 risk-
        adjusted 표준 metric.

    Args:
        alphaSeries: residual return 시리즈 (active vs benchmark).

    Returns:
        IR (raw, 단위 무관). nan/0 가능.

    Example:
        >>> calcIR(alpha)
        0.42

    Guide:
        연환산 = IR × √252 (일별 alpha). IR ≥ 0.5 = 양호. fundamentalLawIR 와
        결합해 IC × √breadth 검증.

    When:
        Active 운용 평가 + AI 잔여 alpha 답변.

    How:
        mean / std (ddof=1).

    Requires:
        alphaSeries ≥ 2.

    Raises:
        없음 — NaN/0 반환.

    See Also:
        - fundamentalLawIR : IC × √breadth
        - icSignificance : IC t-stat

    AIContext:
        raw IR 인용 시 연환산 단위 명시 (일/주/월 등).
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

    Example:
        >>> fundamentalLawIR(0.05, 400)
        1.0

    Requires:
        breadth ≥ 1.

    Raises:
        없음 — breadth < 1 시 0 반환.
    """
    if breadth < 1:
        return 0.0
    return float(ic * np.sqrt(breadth))


def rollingTimeSeriesZscore(series: np.ndarray, window: int) -> np.ndarray:
    """Rolling z-score (Grinold Ch.3 팩터 정규화): z_t = (x_t − μ_w) / σ_w.

    Capabilities:
        Rolling window z-score 표준화 — 시계열 팩터 신호 normalize. Grinold Ch.3
        표준 (factor scaling).

    Args:
        series: 1D 시계열.
        window: 윈도우 크기 (≥ 2).

    Returns:
        z-score 시리즈. 첫 window-1 개는 NaN.

    Example:
        >>> z = rollingTimeSeriesZscore(series, window=60)

    Guide:
        window 60 (분기) 또는 252 (1년) 권장. z 절대값 > 2 = outlier 신호.

    When:
        팩터 시계열 정규화 + AI z-score 답변.

    How:
        각 시점 chunk → mean/std → (x - mu) / sigma.

    Requires:
        series ≥ window + window ≥ 2.

    Raises:
        없음 — std=0 시 NaN.

    See Also:
        - pearsonCorr / spearmanCorr : 정규화 후 상관

    AIContext:
        rolling z 시리즈 → 신호 시계열로 변환 후 백테스트 입력.
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

    Capabilities:
        IC 시계열 → t-stat (mean / SE) + hit rate + 95% CI + isSignificant
        (|t| > 2). Grinold Ch.8 IC 유의성 표준.

    Args:
        icSeries: IC 시계열 (분기 또는 월별).
        nStocks: 한 시점 cross-section 종목 수 (옵션, 결과에 echo).

    Returns:
        dict — meanIC/stdIC/tStat/hitRate/ci95/isSignificant/nPeriods/nStocks.

    Example:
        >>> icSignificance(ic_series)
        {'meanIC': 0.045, 'tStat': 3.2, 'isSignificant': True, ...}

    Guide:
        |t| > 2 = 5% 유의. nStocks > 20 + nPeriods > 12 권장. multiple testing
        보정은 haircutSharpe 사용.

    When:
        팩터 검증 + AI IC 유의성 답변.

    How:
        mean(IC) / (std(IC)/√T) → t-stat → CI → 유의 판정.

    Requires:
        icSeries ≥ 2 관측.

    Raises:
        없음 — 부족 시 NaN dict.

    See Also:
        - calcFactorIC : IC 시계열 생성
        - haircutSharpe : multiple testing 보정

    AIContext:
        t + hitRate + meanIC 3 필드 인용으로 IC 신뢰도 답변.
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

    Capabilities:
        IC 시계열 자기상관 (AR1) → ρ + half-life (반감기) + persistence 라벨
        (high/medium/low/none). 팩터 신호 지속성 정량화.

    Args:
        icSeries: IC 시계열 (분기/월).

    Returns:
        dict — autocorr/halfLifePeriods/persistence.

    Example:
        >>> factorDecayRate(ic)
        {'autocorr': 0.45, 'halfLifePeriods': 0.87, 'persistence': 'medium'}

    Guide:
        persistence high (ρ>0.5) = 신호 지속, low (ρ<0.2) = 빠른 decay.
        rebalance 주기 결정 시 halfLife 참고.

    When:
        팩터 alpha 지속성 + AI rebalance 주기 답변.

    How:
        IC AR(1) lag 1 → ρ → half_life = log(0.5)/log(ρ).

    Requires:
        icSeries ≥ 4.

    Raises:
        없음.

    See Also:
        - icSignificance : t-stat
        - calcFactorIC : IC 시리즈 생성

    AIContext:
        half-life + persistence 라벨 인용으로 신호 지속성 답변.
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

    Capabilities:
        rebalancesPerYear × nStocks × independenceRatio = breadth. fundamentalLawIR
        의 N 추정 보조.

    Args:
        rebalancesPerYear: 연간 리밸런싱 횟수 (12 = 월별).
        nStocks: 한 시점 universe 종목 수.
        independenceRatio: 베팅 독립성 (1 = 완전 독립, 0.5 = 50%).

    Returns:
        breadth (int).

    Example:
        >>> breadthFromFrequency(rebalancesPerYear=12, nStocks=100, independenceRatio=0.8)
        960

    Guide:
        independenceRatio < 1 = 종목 간 상관 (산업 집중) 반영. 일반적으로 0.5
        ~ 0.8.

    When:
        fundamentalLawIR 호출 전 N 추정.

    How:
        rebalancesPerYear × nStocks × clip(independenceRatio, 0, 1).

    Requires:
        rebalancesPerYear/nStocks ≥ 1.

    Raises:
        없음.

    See Also:
        - fundamentalLawIR : IR = IC × √breadth

    AIContext:
        independenceRatio 가정 명시 (0.5 vs 1.0 결과 큰 차이).
    """
    if rebalancesPerYear < 1 or nStocks < 1:
        return 0
    ratio = max(0.0, min(1.0, float(independenceRatio)))
    return int(rebalancesPerYear * nStocks * ratio)


def impliedIRFromICDistribution(icSeries: np.ndarray, breadth: int) -> dict:
    """IC 분포 + breadth → 이론 IR vs 실현 ICIR 비교.

    Capabilities:
        Fundamental Law (IR = IC × √breadth) 이론값과 실현 ICIR (meanIC/stdIC)
        비교 → efficiency 비율. 전략 효율성 정량화.

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

    Example:
        >>> impliedIRFromICDistribution(ic, breadth=400)
        {'meanIC': 0.05, 'theoreticalIR': 1.0, 'realizedICIR': 0.8, 'efficiency': 0.8}

    Guide:
        efficiency 1.0 = 이론대로 실현. < 0.5 = IC volatility 크거나 베팅 비독립.
        > 1.0 = 이론 초과 (sample noise 검증 필요).

    When:
        Grinold fundamental law 검증 + AI 전략 효율성 답변.

    How:
        meanIC × √breadth = theo / meanIC / stdIC = real / 비율.

    Requires:
        icSeries ≥ 2 + breadth ≥ 1.

    Raises:
        없음.

    See Also:
        - fundamentalLawIR : 이론
        - icSignificance : t-stat

    AIContext:
        efficiency 인용으로 "이론 대비 80% 실현" 답변.
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


# 0.10 BC 깸 — snake_case alias 제거.

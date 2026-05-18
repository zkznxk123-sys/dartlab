"""IC/IR metrics — Grinold & Kahn Ch.5-8.

Pearson/Spearman 상관, IR, Fundamental Law (IR = IC × √breadth), IC 유의성
(t-stat), factor decay (AR(1)), breadth 자동 추정. numpy 순수.
"""

from __future__ import annotations

import numpy as np


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

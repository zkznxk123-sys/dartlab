"""꼬리위험 분석 — CVaR, 최대낙폭, Sortino, 하방편차.

학술 근거:
- Artzner et al. (1999): Coherent risk measures (CVaR/Expected Shortfall)
- Sortino & van der Meer (1991): Sortino ratio
"""

from __future__ import annotations

import numpy as np

from dartlab.core.market import resolveMarket
from dartlab.core.polarsUtil import isEmptyDf
from dartlab.quant.screen.dataAccess import fetchOhlcv, ohlcvToArrays


def _tailriskSeries(close: np.ndarray, window: int = 252) -> dict:
    """rolling MDD/CVaR 시계열 — Strategy DSL 입력용."""
    n = len(close)
    rolling_mdd = np.full(n, np.nan, dtype=np.float64)
    rolling_cvar = np.full(n, np.nan, dtype=np.float64)
    log_ret = np.diff(np.log(close), prepend=np.log(close[0]))
    for i in range(window, n):
        win = close[i - window + 1 : i + 1]
        peak = np.maximum.accumulate(win)
        dd = (win - peak) / peak
        rolling_mdd[i] = float(np.min(dd))
        # CVaR 5%
        rets = log_ret[i - window + 1 : i + 1]
        q5 = np.quantile(rets, 0.05)
        rolling_cvar[i] = float(np.mean(rets[rets <= q5])) if (rets <= q5).any() else np.nan
    return {"rolling_mdd": rolling_mdd, "rolling_cvar": rolling_cvar}


def calcTailrisk(
    stockCode: str, *, market: str = "auto", riskFree: float = 0.0, series: bool = False, **kwargs
) -> dict:
    """꼬리위험 종합 분석 — VaR/CVaR + MDD + Sortino/Sharpe.

    Capabilities:
        역사적 시뮬레이션 기반 VaR (95/99%) + Expected Shortfall (CVaR) +
        Maximum Drawdown + currentDrawdown + 하방편차 + Sortino + Sharpe +
        downside capture. Artzner et al. (1999) coherent risk measure 표준.
        annualReturn 은 산술평균 × 252 (CAGR 아님 — 연환산 단순화).

    Args:
        stockCode: 종목코드 또는 ticker.
        market: "KR" | "US" | "auto".
        riskFree: 연환산 무위험수익률 (기본 0.0).
        series: True 면 ``_series`` 키 추가.

    Returns:
        dict:
            - ``var{95,99}`` (float): 일별 VaR.
            - ``cvar{95,99}`` (float): 일별 ES.
            - ``var/cvar*_annual`` (float): 연환산.
            - ``maxDrawdown``/``maxDrawdownDate``/``currentDrawdown``.
            - ``downsideDev``/``sortino``/``sharpe``/``annualReturn``.
            - 또는 ``error`` (str): 데이터 부족 (30 일 미만).

    Raises:
        없음 (error 키 반환).

    Example:
        >>> r = calcTailrisk("005930", riskFree=0.035)
        >>> r["maxDrawdown"], r["cvar95_annual"]
        (-0.32, -0.55)

    Guide:
        - VaR 95% 일별 -3% = 100 일 중 5 일은 -3% 이상 손실 예상.
        - CVaR > VaR 절대값 → tail loss 가 평균보다 큼 (heavy tail).
        - Sortino > Sharpe → 상방 변동성 큰 자산 (성장주 패턴).
        - MDD 시점 (maxDrawdownDate) 함께 인용 시 macro 이벤트 (코로나/금리)
          연결 가능.

    SeeAlso:
        - ``calcVolatility``: GARCH/HAR-RV
        - ``calcMomentum``: 가격 모멘텀
        - ``credit.engine``: 신용 7 축 (본 vol 입력)

    Requires:
        OHLCV 일별 ≥ 30 일.

    AIContext:
        VaR/CVaR + MDD 함께 인용. 단기 (30~60 일) 결과는 sample 적어 신뢰
        제한. annualReturn 산술 vs CAGR 차이 설명 필요 (장기간 차이 큼).

    LLM Specifications:
        AntiPatterns:
            - VaR 인용에 confidence 누락 — 95% vs 99% 명시.
            - annualReturn 을 CAGR 로 단정 — 본 함수는 산술평균 × 252.
        OutputSchema:
            ``{var95, cvar95, var99, cvar99, maxDrawdown, sortino, sharpe,
              annualReturn, downsideDev, ...}``.
        Prerequisites:
            OHLCV ≥ 30 일.
        Freshness:
            일별.
        Dataflow:
            OHLCV → log returns → percentile → VaR/CVaR → cumulative →
            drawdown → downside dev → Sortino/Sharpe.
        TargetMarkets: KR, US (OHLCV 동일 컨벤션).
    """
    market = resolveMarket(stockCode, market)
    ohlcv = fetchOhlcv(stockCode, **kwargs)
    if isEmptyDf(ohlcv):
        return {"error": f"{stockCode} 주가 데이터 없음"}

    arr = ohlcvToArrays(ohlcv)
    if "close" not in arr or len(arr["close"]) < 30:
        return {"error": f"{stockCode} 데이터 부족 (최소 30일 필요)"}

    close = arr["close"]
    n = len(close)
    daily_returns = np.diff(np.log(close))

    result: dict = {
        "stockCode": stockCode,
        "market": market,
        "dataPoints": n,
    }
    if series:
        result["_series"] = _tailriskSeries(close)

    # ── VaR & CVaR (역사적 시뮬레이션) ──
    for confidence, label in [(0.95, "95"), (0.99, "99")]:
        var_pct = float(np.percentile(daily_returns, (1 - confidence) * 100))
        # CVaR = VaR 이하 평균 (Expected Shortfall)
        tail = daily_returns[daily_returns <= var_pct]
        cvar = float(np.mean(tail)) if len(tail) > 0 else var_pct

        result[f"var{label}"] = round(var_pct, 6)
        result[f"cvar{label}"] = round(cvar, 6)
        # 연환산
        result[f"var{label}_annual"] = round(var_pct * np.sqrt(252), 4)
        result[f"cvar{label}_annual"] = round(cvar * np.sqrt(252), 4)

    # ── 최대낙폭 (Maximum Drawdown) ──
    cumulative = np.cumprod(1 + np.diff(close) / close[:-1])
    cumulative = np.insert(cumulative, 0, 1.0)
    running_max = np.maximum.accumulate(cumulative)
    drawdowns = (cumulative - running_max) / running_max
    max_dd = float(np.min(drawdowns))
    max_dd_idx = int(np.argmin(drawdowns))

    result["maxDrawdown"] = round(max_dd, 4)
    if "date" in arr and max_dd_idx < len(arr["date"]):
        result["maxDrawdownDate"] = str(arr["date"][max_dd_idx])

    # 현재 낙폭
    current_dd = float(drawdowns[-1])
    result["currentDrawdown"] = round(current_dd, 4)

    # ── 하방편차 (Downside Deviation) ──
    # MAR = 0 (무위험수익률 0 가정)
    negative_returns = daily_returns[daily_returns < 0]
    downside_dev = float(np.sqrt(np.mean(negative_returns**2))) if len(negative_returns) > 0 else 0
    result["downsideDev"] = round(downside_dev * np.sqrt(252), 4)

    # ── Sortino Ratio ──
    # (annualReturn - riskFree) / 하방편차
    annual_return = float(np.mean(daily_returns) * 252)
    excess = annual_return - riskFree
    if downside_dev > 0:
        sortino = excess / (downside_dev * np.sqrt(252))
    else:
        sortino = 0.0
    result["sortino"] = round(float(sortino), 4)
    result["annualReturn"] = round(annual_return, 4)
    result["riskFree"] = round(float(riskFree), 4)

    # ── Calmar Ratio ──
    # 초과수익률 / |최대낙폭|
    if abs(max_dd) > 0:
        calmar = excess / abs(max_dd)
    else:
        calmar = 0.0
    result["calmar"] = round(float(calmar), 4)

    # ── 변동성 (연환산) ──
    vol = float(np.std(daily_returns) * np.sqrt(252))
    result["volatility"] = round(vol, 4)

    # ── Sharpe Ratio ──
    if vol > 0:
        sharpe = excess / vol
    else:
        sharpe = 0.0
    result["sharpe"] = round(float(sharpe), 4)

    # ── 왜도/첨도 ──
    if len(daily_returns) >= 30:
        skewness = float(_skewness(daily_returns))
        kurtosis = float(_kurtosis(daily_returns))
        result["skewness"] = round(skewness, 4)
        result["kurtosis"] = round(kurtosis, 4)
        # 꼬리위험 등급:
        # - high: 음의 왜도 + 높은 첨도(좌측 두꺼운 꼬리, 손실 편중)
        # - medium-loss: 음의 왜도, 정상 첨도
        # - medium-fat: 양의 왜도지만 매우 높은 첨도(양측 꼬리 모두 두꺼움)
        # - low: 그 외
        if skewness < -0.5 and kurtosis > 4:
            result["tailRiskGrade"] = "high"
        elif skewness < 0 and kurtosis > 3:
            result["tailRiskGrade"] = "medium-loss"
        elif kurtosis > 5:
            result["tailRiskGrade"] = "medium-fat"
        else:
            result["tailRiskGrade"] = "low"

    # ── 극단 손실 빈도 ──
    # 일일 수익률 -3% 이하 빈도
    extreme_losses = np.sum(daily_returns < -0.03)
    result["extremeLossDays"] = int(extreme_losses)
    result["extremeLossFreq"] = round(float(extreme_losses / len(daily_returns)), 4)

    return result


def _skewness(x: np.ndarray) -> float:
    """3차 중심적률 / 표준편차³."""
    n = len(x)
    if n < 3:
        return 0.0
    m = np.mean(x)
    s = np.std(x, ddof=1)
    if s == 0:
        return 0.0
    return float((n / ((n - 1) * (n - 2))) * np.sum(((x - m) / s) ** 3))


def _kurtosis(x: np.ndarray) -> float:
    """4차 중심적률 / 표준편차⁴ (excess kurtosis)."""
    n = len(x)
    if n < 4:
        return 0.0
    m = np.mean(x)
    s = np.std(x, ddof=1)
    if s == 0:
        return 0.0
    k = float(np.mean(((x - m) / s) ** 4))
    # excess kurtosis (정규분포 = 0)
    return k - 3.0

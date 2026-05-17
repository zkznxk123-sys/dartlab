"""변동성 분석 — GARCH(1,1), HAR-RV, 변동성 기간구조.

학술 근거:
- Bollerslev (1986): GARCH(1,1)
- Corsi (2009): HAR-RV 모델
"""

from __future__ import annotations

import numpy as np

from dartlab.core.market import resolveMarket
from dartlab.core.polarsUtil import isEmptyDf
from dartlab.quant.screen.dataAccess import fetchOhlcv, ohlcvToArrays


def _volatilitySeries(close: np.ndarray, window: int = 20) -> dict:
    """rolling 실현 변동성 시계열 — Strategy DSL 입력용."""
    n = len(close)
    log_ret = np.diff(np.log(close), prepend=np.log(close[0]))
    realized = np.full(n, np.nan, dtype=np.float64)
    for i in range(window, n):
        realized[i] = float(np.std(log_ret[i - window + 1 : i + 1]) * np.sqrt(252))
    # GARCH 동적 σ²_t (단순 EWMA σ — 외부 의존 0)
    lam = 0.94
    sigma2 = np.full(n, np.nan, dtype=np.float64)
    sigma2[0] = log_ret[0] ** 2
    for i in range(1, n):
        sigma2[i] = lam * sigma2[i - 1] + (1 - lam) * log_ret[i] ** 2
    return {
        "realized_vol": realized,
        "garch_vol": np.sqrt(sigma2 * 252),
    }


def calcVolatility(
    stockCode: str,
    *,
    market: str = "auto",
    series: bool = False,
    forecast: bool = False,
    forecastHorizon: int = 5,
    **kwargs,
) -> dict:
    """변동성 종합 분석 — 실현 / HAR-RV / GARCH(1,1) / regime / forecast.

    Capabilities:
        다중 기간 실현 변동성 (5/20/60/120/252 d) + HAR-RV (Corsi 2009, daily/
        weekly/monthly RV 회귀) + GARCH(1,1) MLE 적합 + 변동성 regime 분류 +
        h-step 분산 예측 (Bollerslev 1986 closed form). GARCH 미적합 시 EWMA
        λ=0.94 stationary fallback. forecastHorizon 기본 5 일.

    Args:
        stockCode: 종목코드 (KR 6자리) 또는 ticker (US).
        market: "KR" | "US" | "auto".
        series: True 면 ``_series`` 키 추가 (Strategy DSL 입력용 rolling vol).
        forecast: True 면 GARCH h-step variance forecast 추가.
        forecastHorizon: forecast=True 시 예측 일수 (기본 5).

    Returns:
        dict:
            - ``realizedVol_{5,20,60,120,252}d`` (float): 연율화 vol.
            - ``garchVol`` (float): GARCH(1,1) 추정.
            - ``harRV`` (float): HAR-RV 예측.
            - ``volRegime`` (str): "low"|"normal"|"high".
            - ``volTermStructure`` (dict): 단·장기 vol 비교.
            - ``_series`` (dict, optional, series=True): {realized_vol,
              garch_vol} 길이 N.
            - ``forecastVar_h{H}``/``forecastVol_h{H}``/``forecastVolModel``
              (optional, forecast=True).
            - 또는 ``error`` (str): 데이터 부족.

    Raises:
        없음 (모든 실패는 error 키).

    Example:
        >>> r = calcVolatility("005930", forecast=True, forecastHorizon=5)
        >>> r["realizedVol_20d"], r["volRegime"]
        (0.28, 'normal')

    Guide:
        - 최소 60 일 데이터 필요 (그 미만 error).
        - HAR-RV 는 66 일 이상 (long-memory 효과 반영).
        - GARCH vol 와 realized 60d vol 차이가 크면 regime 전환 (low→high)
          의심.
        - forecast 는 short horizon (≤ 5d) 신뢰, 장기는 mean reversion 가정
          GARCH 의 한계.

    See Also:
        - ``calcTailRisk``: VaR/CVaR
        - ``calcMomentum``: 가격 모멘텀
        - ``synth.indicators.volatility``: ATR/BB width

    When:
        Quant risk + 변동성 regime 분류 + GARCH 예측 답변 진입점.

    How:
        OHLCV → log returns → 다중 윈도우 실현 vol (5/20/60/120/252d) → HAR-RV
        회귀 + GARCH(1,1) MLE → regime 분류 → (옵션) h-step forecast.

    Requires:
        OHLCV 일별 시계열 ≥ 60 일.

    AIContext:
        realizedVol vs garchVol 분리 인용 — 후자는 모델 추정, 전자는 관측.
        volRegime 라벨 단독 인용 금지, vol 절대값 + 5d/252d 비율 함께.

    LLM Specifications:
        AntiPatterns:
            - garchVol 단독 인용 — 모델 가정 (조건부 정규) 의 한계.
            - 60 일 미만에 본 함수 호출 — error 반환.
        OutputSchema:
            ``{realizedVol_*: float, garchVol: float, harRV: float,
              volRegime: str, volTermStructure: dict, ...}``.
        Prerequisites:
            OHLCV 일별 ≥ 60 일 (HAR-RV 위해 권장 ≥ 66 일).
        Freshness:
            일별 (최신 종가까지).
        Dataflow:
            OHLCV → log returns → 다중 윈도우 실현 vol → HAR-RV 회귀 →
            GARCH MLE → regime 분류 → (옵션) h-step forecast.
        TargetMarkets: KR (KRX OHLCV), US (NYSE/NASDAQ).
    """
    market = resolveMarket(stockCode, market)
    ohlcv = fetchOhlcv(stockCode, **kwargs)
    if isEmptyDf(ohlcv):
        return {"error": f"{stockCode} 주가 데이터 없음"}

    arr = ohlcvToArrays(ohlcv)
    close = arr.get("close")
    if close is None or len(close) < 60:
        return {"error": f"{stockCode} 데이터 부족 (최소 60일)"}

    n = len(close)
    log_returns = np.diff(np.log(close))

    result: dict = {
        "stockCode": stockCode,
        "market": market,
        "dataPoints": n,
    }
    if series:
        result["_series"] = _volatilitySeries(close)

    # ── 실현 변동성 (다중 기간) ──
    for label, window in [("5d", 5), ("20d", 20), ("60d", 60), ("120d", 120), ("252d", 252)]:
        if len(log_returns) >= window:
            rv = float(np.std(log_returns[-window:]) * np.sqrt(252))
            result[f"realizedVol_{label}"] = round(rv, 4)

    # ── HAR-RV 모델 (Corsi 2009) ──
    # RV_t+1 = β0 + β1*RV_d + β2*RV_w + β3*RV_m + ε
    if len(log_returns) >= 66:
        rv_daily = log_returns**2
        rv_d = _rollingMean(rv_daily, 1)
        rv_w = _rollingMean(rv_daily, 5)
        rv_m = _rollingMean(rv_daily, 22)

        # OLS fit (최근 44일 사용)
        valid_start = 22  # rv_m이 유효한 시점부터
        if len(rv_d) > valid_start + 22:
            y = rv_daily[valid_start + 1 :][:44]
            X = np.column_stack(
                [
                    np.ones(44),
                    rv_d[valid_start:][:44],
                    rv_w[valid_start:][:44],
                    rv_m[valid_start:][:44],
                ]
            )
            if len(y) == 44 and X.shape[0] == 44:
                try:
                    beta = np.linalg.lstsq(X, y, rcond=None)[0]
                    # 1일 ahead 예측
                    x_latest = np.array([1.0, rv_d[-1], rv_w[-1], rv_m[-1]])
                    har_forecast = float(np.dot(beta, x_latest))
                    har_vol = float(np.sqrt(max(har_forecast, 0) * 252))
                    result["harRV"] = round(har_vol, 4)
                    result["harCoeffs"] = {
                        "intercept": round(float(beta[0]), 8),
                        "daily": round(float(beta[1]), 4),
                        "weekly": round(float(beta[2]), 4),
                        "monthly": round(float(beta[3]), 4),
                    }
                except np.linalg.LinAlgError:
                    pass

    # ── GARCH(1,1) (Bollerslev 1986) ──
    # σ²_t = ω + α·ε²_{t-1} + β·σ²_{t-1}
    if len(log_returns) >= 100:
        garch_result = _fitGarch11(log_returns[-252:] if len(log_returns) >= 252 else log_returns)
        if garch_result:
            result["garchVol"] = round(garch_result["forecastVol"], 4)
            result["garchParams"] = {
                "omega": round(garch_result["omega"], 10),
                "alpha": round(garch_result["alpha"], 4),
                "beta": round(garch_result["beta"], 4),
                "persistence": round(garch_result["alpha"] + garch_result["beta"], 4),
            }
            # 장기 변동성
            persistence = garch_result["alpha"] + garch_result["beta"]
            if persistence < 1:
                long_run_var = garch_result["omega"] / (1 - persistence)
                result["garchLongRunVol"] = round(float(np.sqrt(long_run_var * 252)), 4)

    # ── 변동성 기간구조 ──
    term_structure = {}
    for label in ["5d", "20d", "60d", "120d", "252d"]:
        key = f"realizedVol_{label}"
        if key in result:
            term_structure[label] = result[key]
    result["volTermStructure"] = term_structure

    # 기간구조 형태
    vols = list(term_structure.values())
    if len(vols) >= 3:
        if vols[0] > vols[-1] * 1.2:
            result["volCurveShape"] = "backwardation"  # 단기 > 장기 (스트레스)
        elif vols[-1] > vols[0] * 1.2:
            result["volCurveShape"] = "contango"  # 장기 > 단기 (정상)
        else:
            result["volCurveShape"] = "flat"

    # ── 변동성 레짐 ──
    if "realizedVol_20d" in result:
        rv20 = result["realizedVol_20d"]
        if rv20 > 0.5:
            result["volRegime"] = "extreme"
        elif rv20 > 0.3:
            result["volRegime"] = "high"
        elif rv20 > 0.15:
            result["volRegime"] = "normal"
        else:
            result["volRegime"] = "low"

    # ── h-step ahead 변동성 예측 (GARCH(1,1) closed form 또는 EWMA fallback) ──
    if forecast:
        h = max(1, int(forecastHorizon))
        garch = result.get("garchParams")
        forecast_var: float | None = None
        model_used = None
        if garch is not None and len(log_returns) > 0:
            omega = float(garch["omega"])
            alpha_g = float(garch["alpha"])
            beta_g = float(garch["beta"])
            persistence = alpha_g + beta_g
            # σ²_t (마지막 in-sample variance) 추정
            mean_r = float(np.mean(log_returns))
            resid_last = float(log_returns[-1] - mean_r)
            # 1-step ahead var (already computed by _fit_garch11 → forecastVol). 역산:
            sigma2_t = (float(result["garchVol"]) ** 2 / 252.0) if "garchVol" in result else float(np.var(log_returns))
            # h-step ahead: σ²_{t+h} = ω·Σ_{i=0..h-1}(α+β)^i + (α+β)^h · σ²_t
            if persistence < 1.0 and persistence > 0:
                geo_sum = (1.0 - persistence**h) / (1.0 - persistence)
                forecast_var = omega * geo_sum + (persistence**h) * sigma2_t
            else:
                forecast_var = sigma2_t
            model_used = "garch11"
        elif len(log_returns) >= 20:
            # EWMA fallback: σ²_{t+h} = σ²_t (RiskMetrics IGARCH)
            ewma_lam = 0.94
            sigma2_ewma = float(log_returns[-1] ** 2)
            for i in range(max(0, len(log_returns) - 60), len(log_returns)):
                sigma2_ewma = ewma_lam * sigma2_ewma + (1 - ewma_lam) * float(log_returns[i] ** 2)
            forecast_var = sigma2_ewma
            model_used = "ewma94"
        if forecast_var is not None and forecast_var >= 0:
            forecast_vol = float(np.sqrt(forecast_var * 252))
            result[f"forecastVar_h{h}"] = round(forecast_var, 10)
            result[f"forecastVol_h{h}"] = round(forecast_vol, 4)
            result["forecastVolModel"] = model_used
            result["forecastHorizon"] = h

    return result


def _rollingMean(arr: np.ndarray, window: int) -> np.ndarray:
    """간단 rolling mean."""
    if window <= 1:
        return arr.copy()
    kernel = np.ones(window) / window
    return np.convolve(arr, kernel, mode="same")


def _fitGarch11(returns: np.ndarray) -> dict | None:
    """GARCH(1,1) numpy MLE — Nelder-Mead simplex.

    σ²_t = ω + α·ε²_{t-1} + β·σ²_{t-1}
    """
    n = len(returns)
    if n < 50:
        return None

    mean_r = np.mean(returns)
    resid = returns - mean_r
    var_init = float(np.var(resid))

    def negLogLikelihood(params) -> float:
        """GARCH(1,1) 음의 로그우도 — Nelder-Mead 최적화 목적함수.

        Capabilities:
            - GARCH(1,1) sigma² 시계열 + Gaussian log-likelihood 누적 → 음수 반환
            - 파라미터 제약 (ω > 0, α ≥ 0, β ≥ 0, α+β < 1) 위반 시 1e10 penalty

        Args:
            params: ``[omega, alpha, beta]`` GARCH 파라미터.

        Returns:
            float — 음의 로그우도 (최적화 minimize target).

        Guide:
            Bollerslev 1986 GARCH(1,1) 표준. closure 내부 함수 — outer ``calcGARCH`` 가 사용.

        When:
            GARCH 파라미터 추정 internal + AI 변동성 모델링 답변.

        How:
            sigma2 시계열 → log + resid²/sigma2 누적 → -ll.

        Requires:
            outer scope 의 returns + resid + var_init.

        Raises:
            없음 — 제약 위반 시 penalty 반환.

        Example:
            >>> negLogLikelihood([0.001, 0.08, 0.85])
            -1240.5

        SeeAlso:
            - calcGARCH : 외부 wrapper
            - _nelderMead : 옵티마이저

        AIContext:
            GARCH 추정의 internal objective. AI 사용자에게 직접 노출 X.
        """
        omega, alpha, beta = params
        if omega <= 0 or alpha < 0 or beta < 0 or alpha + beta >= 1:
            return 1e10

        sigma2 = np.empty(n)
        sigma2[0] = var_init

        for t in range(1, n):
            sigma2[t] = omega + alpha * resid[t - 1] ** 2 + beta * sigma2[t - 1]
            if sigma2[t] <= 0:
                return 1e10

        ll = -0.5 * np.sum(np.log(sigma2) + resid**2 / sigma2)
        return -ll

    # Nelder-Mead simplex optimization
    best_params = _nelderMead(
        negLogLikelihood,
        x0=np.array([var_init * 0.05, 0.08, 0.85]),
        maxIter=500,
    )

    if best_params is None:
        return None

    omega, alpha, beta = best_params
    if omega <= 0 or alpha < 0 or beta < 0 or alpha + beta >= 1:
        return None

    # 1일 ahead 예측
    sigma2 = np.empty(n)
    sigma2[0] = var_init
    for t in range(1, n):
        sigma2[t] = omega + alpha * resid[t - 1] ** 2 + beta * sigma2[t - 1]

    forecast_var = omega + alpha * resid[-1] ** 2 + beta * sigma2[-1]
    forecast_vol = float(np.sqrt(max(forecast_var, 0) * 252))

    return {
        "omega": float(omega),
        "alpha": float(alpha),
        "beta": float(beta),
        "forecastVol": forecast_vol,
    }


def _nelderMead(fn, x0: np.ndarray, maxIter: int = 500, tol: float = 1e-8) -> np.ndarray | None:
    """간이 Nelder-Mead simplex optimizer (numpy only)."""
    n = len(x0)
    # simplex 초기화
    simplex = np.zeros((n + 1, n))
    simplex[0] = x0
    for i in range(n):
        point = x0.copy()
        point[i] *= 1.05 if point[i] != 0 else 0.00025
        simplex[i + 1] = point

    f_values = np.array([fn(simplex[i]) for i in range(n + 1)])

    for _ in range(maxIter):
        # 정렬
        order = np.argsort(f_values)
        simplex = simplex[order]
        f_values = f_values[order]

        # 수렴 체크
        if np.max(np.abs(f_values[-1] - f_values[0])) < tol:
            break

        # centroid (worst 제외)
        centroid = np.mean(simplex[:-1], axis=0)

        # reflection
        xr = centroid + (centroid - simplex[-1])
        fr = fn(xr)

        if fr < f_values[0]:
            # expansion
            xe = centroid + 2 * (centroid - simplex[-1])
            fe = fn(xe)
            if fe < fr:
                simplex[-1] = xe
                f_values[-1] = fe
            else:
                simplex[-1] = xr
                f_values[-1] = fr
        elif fr < f_values[-2]:
            simplex[-1] = xr
            f_values[-1] = fr
        else:
            # contraction
            xc = centroid + 0.5 * (simplex[-1] - centroid)
            fc = fn(xc)
            if fc < f_values[-1]:
                simplex[-1] = xc
                f_values[-1] = fc
            else:
                # shrink
                for i in range(1, n + 1):
                    simplex[i] = simplex[0] + 0.5 * (simplex[i] - simplex[0])
                    f_values[i] = fn(simplex[i])

    best = simplex[np.argmin(f_values)]
    if fn(best) > 1e9:
        return None
    return best

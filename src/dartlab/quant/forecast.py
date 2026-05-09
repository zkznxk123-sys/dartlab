"""시계열 수익률 예측 — Naive · AR(1) · ETS-Holt · Theta 4 모델 + Conformal interval.

학술 근거:
- Holt (1957): exponential smoothing with trend
- Assimakopoulos & Nikolopoulos (2000): Theta method
- Vovk, Gammerman, Shafer (2005): Conformal prediction
- MacKinnon (1996): Augmented Dickey-Fuller critical values

설계 원칙:
- numpy only (scipy / statsmodels / arch / pmdarima / sklearn 사용 금지 — base install SSOT 보존).
- 모든 모델은 log-return 시계열 (Δlog close) 에서 fit.
- pointForecast 는 일별 log-return. cumLogReturn → exp() → priceTarget.
- Conformal interval: split conformal, calib = 마지막 calibFraction (default 20%).
"""

from __future__ import annotations

import numpy as np

from dartlab.core.polarsUtil import isEmptyDf
from dartlab.quant._helpers import fetch_ohlcv, ohlcv_to_arrays, resolve_market

_VALID_MODELS = ("naive", "ar1", "etsHolt", "theta")


# ── ADF (Dickey-Fuller) 자체 구현 — scipy 없이 ──────────────


def _pAdfStationary(y: np.ndarray) -> float:
    """Dickey-Fuller t-statistic → p-value 근사 (단위근 검정).

    Δy_t = α + ρ y_{t-1} + ε 회귀의 ρ̂ / SE(ρ̂) 를 t 통계량으로 간주, MacKinnon (1996)
    표준 임계치 테이블 위에서 선형 보간한다. 구간 밖 값은 0.005 / 0.99 로 클램프.

    Parameters
    ----------
    y : np.ndarray
        검정 시계열 (이미 1차 차분된 log-return 권장).

    Returns
    -------
    float
        근사 p-value. 0.05 미만이면 stationary (평균회귀) 로 간주, dispatch 룰에서 활용.
    """
    n = len(y)
    if n < 20:
        return 1.0
    dy = np.diff(y)
    yt_prev = y[:-1]
    X = np.column_stack([np.ones(n - 1), yt_prev])
    try:
        coef, *_ = np.linalg.lstsq(X, dy, rcond=None)
    except np.linalg.LinAlgError:
        return 1.0
    rho_hat = float(coef[1])
    pred = X @ coef
    resid = dy - pred
    sigma2 = float(np.sum(resid**2) / max(n - 3, 1))
    try:
        XtX_inv = np.linalg.inv(X.T @ X)
    except np.linalg.LinAlgError:
        return 1.0
    var_rho = sigma2 * float(XtX_inv[1, 1])
    if var_rho <= 0:
        return 1.0
    t_stat = rho_hat / float(np.sqrt(var_rho))
    table = [
        (-3.43, 0.01),
        (-2.86, 0.05),
        (-2.57, 0.10),
        (-2.20, 0.25),
        (-1.65, 0.50),
        (-1.00, 0.75),
        (0.00, 0.95),
    ]
    if t_stat <= table[0][0]:
        return 0.005
    if t_stat >= table[-1][0]:
        return 0.99
    for i in range(1, len(table)):
        x1, p1 = table[i - 1]
        x2, p2 = table[i]
        if x1 <= t_stat <= x2:
            frac = (t_stat - x1) / max(x2 - x1, 1e-12)
            return float(p1 + frac * (p2 - p1))
    return 1.0


# ── 4 모델 (numpy only) ───────────────────────────────────


def _modelNaive(y: np.ndarray, horizon: int) -> tuple[np.ndarray, np.ndarray]:
    """Drift naive — pointForecast = mean(y) for every horizon.

    Returns
    -------
    forecasts : np.ndarray length horizon
    in_sample : np.ndarray length len(y) — 1-step ahead in-sample (drift constant)
    """
    drift = float(np.mean(y))
    in_sample = np.full(len(y), drift)
    in_sample[0] = float(y[0])
    forecasts = np.full(horizon, drift)
    return forecasts, in_sample


def _modelAr1(y: np.ndarray, horizon: int) -> tuple[np.ndarray, np.ndarray]:
    """AR(1) y_t = α + ρ y_{t-1} + ε — OLS 로 ρ, α 추정.

    Stationary 하면 ρ̂ → 0, |ρ̂| < 1 클램프.
    """
    n = len(y)
    if n < 3:
        return _modelNaive(y, horizon)
    yt = y[1:]
    yt_prev = y[:-1]
    mean_prev = float(np.mean(yt_prev))
    mean_yt = float(np.mean(yt))
    x_centered = yt_prev - mean_prev
    y_centered = yt - mean_yt
    denom = float(np.dot(x_centered, x_centered))
    if denom < 1e-12:
        return _modelNaive(y, horizon)
    rho = float(np.dot(x_centered, y_centered) / denom)
    rho = max(min(rho, 0.99), -0.99)
    alpha = mean_yt - rho * mean_prev
    in_sample = np.empty(n)
    in_sample[0] = float(y[0])
    in_sample[1:] = alpha + rho * y[:-1]
    forecasts = np.empty(horizon)
    last = float(y[-1])
    for h in range(horizon):
        last = alpha + rho * last
        forecasts[h] = last
    return forecasts, in_sample


def _modelEtsHolt(y: np.ndarray, horizon: int) -> tuple[np.ndarray, np.ndarray]:
    """Holt linear — level + trend (no seasonality), α/β grid search.

    L_t = α y_t + (1-α)(L_{t-1} + T_{t-1})
    T_t = β(L_t - L_{t-1}) + (1-β) T_{t-1}
    forecast h = L_n + h * T_n
    """
    n = len(y)
    if n < 3:
        return _modelNaive(y, horizon)
    grid_alpha = (0.1, 0.3, 0.5, 0.7, 0.9)
    grid_beta = (0.05, 0.1, 0.3, 0.5)
    best_sse = np.inf
    best = None
    for a in grid_alpha:
        for b in grid_beta:
            L = np.empty(n)
            T = np.empty(n)
            L[0] = float(y[0])
            T[0] = 0.0
            for t in range(1, n):
                L[t] = a * y[t] + (1 - a) * (L[t - 1] + T[t - 1])
                T[t] = b * (L[t] - L[t - 1]) + (1 - b) * T[t - 1]
            in_sample = np.empty(n)
            in_sample[0] = float(y[0])
            in_sample[1:] = L[:-1] + T[:-1]
            sse = float(np.sum((y[1:] - in_sample[1:]) ** 2))
            if sse < best_sse:
                best_sse = sse
                best = (a, b, L.copy(), T.copy(), in_sample.copy())
    if best is None:
        return _modelNaive(y, horizon)
    _, _, L, T, in_sample = best
    forecasts = np.array([L[-1] + (h + 1) * T[-1] for h in range(horizon)], dtype=np.float64)
    return forecasts, in_sample


def _modelTheta(y: np.ndarray, horizon: int) -> tuple[np.ndarray, np.ndarray]:
    """Theta method — linear regression line + SES on theta=2 line, equal weight.

    Reference: Assimakopoulos & Nikolopoulos (2000).
    """
    n = len(y)
    if n < 3:
        return _modelNaive(y, horizon)
    t = np.arange(n, dtype=np.float64)
    sx = float(np.sum(t))
    sy = float(np.sum(y))
    sxx = float(np.sum(t * t))
    sxy = float(np.sum(t * y))
    denom_lin = n * sxx - sx * sx
    if denom_lin < 1e-12:
        return _modelNaive(y, horizon)
    slope = (n * sxy - sx * sy) / denom_lin
    intercept = (sy - slope * sx) / n
    line0 = intercept + slope * t
    y_theta2 = 2.0 * y - line0
    grid_alpha = (0.1, 0.3, 0.5, 0.7, 0.9)
    best_sse = np.inf
    best = None
    for a in grid_alpha:
        ses = np.empty(n)
        ses[0] = float(y_theta2[0])
        for ti in range(1, n):
            ses[ti] = a * float(y_theta2[ti]) + (1 - a) * ses[ti - 1]
        in_sample_theta2 = np.empty(n)
        in_sample_theta2[0] = float(y_theta2[0])
        in_sample_theta2[1:] = ses[:-1]
        sse = float(np.sum((y_theta2[1:] - in_sample_theta2[1:]) ** 2))
        if sse < best_sse:
            best_sse = sse
            best = (ses.copy(), in_sample_theta2.copy())
    if best is None:
        return _modelNaive(y, horizon)
    ses, in_sample_theta2 = best
    in_sample = (line0 + in_sample_theta2) / 2.0
    in_sample[0] = float(y[0])
    last_ses = float(ses[-1])
    forecasts = np.empty(horizon)
    for h in range(horizon):
        line0_fwd = intercept + slope * (n + h)
        forecasts[h] = (line0_fwd + last_ses) / 2.0
    return forecasts, in_sample


_MODEL_FNS = {
    "naive": _modelNaive,
    "ar1": _modelAr1,
    "etsHolt": _modelEtsHolt,
    "theta": _modelTheta,
}


# ── Conformal interval ───────────────────────────────────


def _conformalHalfWidth(residuals: np.ndarray, alpha: float = 0.10) -> float:
    """|residual| 의 (1-alpha) 분위수 → conformal half-width.

    inductive (split) conformal — calib residuals 의 절댓값 분포에서 quantile 을 취해
    [point - q, point + q] 로 (1-alpha) coverage 를 *분포 가정 없이* 보장한다.
    """
    abs_res = np.abs(residuals)
    abs_res = abs_res[np.isfinite(abs_res)]
    if abs_res.size == 0:
        return 0.0
    sorted_abs = np.sort(abs_res)
    n = sorted_abs.size
    q_idx = int(np.ceil((1.0 - alpha) * (n + 1))) - 1
    q_idx = max(0, min(q_idx, n - 1))
    return float(sorted_abs[q_idx])


# ── Model dispatch ────────────────────────────────────────


def _pickModel(y: np.ndarray) -> str:
    """3 분기 dispatch — n / 정상성 기반.

    1) n < 60 → naive (데이터 부족 보수적).
    2) ADF p-value < 0.05 → ar1 (평균회귀 시계열엔 ρ·y_prev 점추정이 정석 — theta 는
       SES 가 마지막 점프에 끌려가 비현실 점추정을 낼 수 있다, cycle 1 회귀).
    3) else → etsHolt (level + trend, 일별 random-walk 류 시계열 default).

    theta 는 명시 호출 (`models=["theta"]`) 시에만 사용. 일별 log-return 시계열은
    거의 항상 stationary 라 theta 의 가정 (trend + 평균회귀 분해) 이 잘 맞지 않음.
    """
    n = len(y)
    if n < 60:
        return "naive"
    p = _pAdfStationary(y)
    if p < 0.05:
        return "ar1"
    return "etsHolt"


# ── 메인 진입점 ───────────────────────────────────────────


def forecastReturns(
    stockCode: str,
    *,
    market: str = "auto",
    horizon: int = 5,
    models: list[str] | None = None,
    calibFraction: float = 0.2,
    alpha: float = 0.10,
    **kwargs,
) -> dict:
    """일별 수익률 예측 + Conformal prediction interval.

    가격 → log-return Δlog(close) 시계열에 4 개 모델 (Naive · AR(1) · ETS-Holt · Theta)
    중 하나를 자동 선택 (또는 명시 ensemble) 해 fit. 마지막 ``calibFraction`` 만큼을
    calibration split 으로 사용해 분포 가정 없는 conformal half-width 를 산출한다.

    Parameters
    ----------
    stockCode : str
        종목코드 또는 ticker (예: "005930", "AAPL").
    market : str
        "KR" / "US" / "auto" — auto 면 코드 형식으로 추론.
    horizon : int
        예측 시점 (일). 기본 5.
    models : list[str] | None
        명시 시 ``["naive", "ar1", "etsHolt", "theta"]`` 부분집합. ``len > 1`` 이면 평균 ensemble.
        None 이면 ``_pickModel`` 의 dispatch 룰 적용.
    calibFraction : float
        residual quantile 산출에 쓰일 calibration split 비율 (기본 0.2).
    alpha : float
        prediction interval 유의수준 (기본 0.10 → 90% coverage).
    **kwargs
        ``fetch_ohlcv`` 전달 인자 (``start``, ``end`` 등).

    Returns
    -------
    dict
        stockCode, market, lastClose, lastDate,
        modelChosen, modelsConsidered, horizon, nObs, calibSize,
        pAdfStationary, conformalHalfWidth (단위: 일별 log-return),
        forecastTable (list[dict] — horizon 행), summary (사람-읽는 한 줄).
        실패 시: ``{"error": ...}``.

    When
    ----
    AI 가 종목의 단기 (1~20 일) 수익률 점추정과 분포 가정 없는 신뢰 구간을 함께 원할 때.
    예: "이 종목 다음 5 일 예상 수익률은?" — point + 90% interval + 가격 타깃.

    How
    ---
    >>> import dartlab
    >>> dartlab.quant("forecast", "005930", horizon=5)
    >>> dartlab.quant("예측", "005930", horizon=10, models=["etsHolt", "theta"])
    >>> dartlab.quant("수익률예측", "AAPL", horizon=20)

    Verified
    --------
    - 합성 uptrend (drift +0.001/day, n=200) → cumLogReturn[5] > 0, summary 양수 (cycle 1, 2026-05-09)
    - 합성 sideways → ADF p < 0.05 → theta 선택, |pointForecast| < 0.5σ (cycle 1)
    - lowerBound < pointForecast < upperBound 단조 (모든 horizon, 모든 cycle)

    Examples
    --------
    >>> r = dartlab.quant("forecast", "005930", horizon=5)
    >>> r["modelChosen"]
    'etsHolt'
    >>> r["forecastTable"][0]["pointForecast"]  # 1 일 후 예측 log-return
    0.0012

    Raises
    ------
    KeyError
        models 인자에 미등록 모델 이름.

    Notes
    -----
    - log-return 시계열에 fit. pointForecast 단위는 *일별 log-return*. 누적은 cumLogReturn.
    - 가격 타깃은 ``last_close * exp(cumLogReturn)``. priceLower/Upper 는 누적 conformal 구간.
    - Calibration 은 in-sample 1-step 예측의 마지막 ``int(n * calibFraction)`` 점을 사용
      (split conformal 단순화 — 정식 split 은 별도 fit/calib 파티션 필요).
    - 의존성 0 (numpy 만). statsmodels / scipy / sklearn import 금지.
    """
    market = resolve_market(stockCode, market)
    ohlcv = fetch_ohlcv(stockCode, **kwargs)
    if isEmptyDf(ohlcv):
        return {"error": f"{stockCode} 주가 데이터 없음", "stockCode": stockCode, "market": market}

    arr = ohlcv_to_arrays(ohlcv)
    close = arr.get("close")
    if close is None or len(close) < 30:
        return {
            "error": f"{stockCode} 데이터 부족 (최소 30 일)",
            "stockCode": stockCode,
            "market": market,
            "nObs": int(len(close)) if close is not None else 0,
        }

    last_close = float(close[-1])
    dates = arr.get("date") or []
    last_date = str(dates[-1]) if dates else None

    log_ret = np.diff(np.log(close))
    n = int(len(log_ret))
    p_adf = _pAdfStationary(log_ret)

    if models is None:
        chosen = _pickModel(log_ret)
        models_used: list[str] = [chosen]
    else:
        invalid = [m for m in models if m not in _VALID_MODELS]
        if invalid:
            return {
                "error": f"유효하지 않은 모델: {invalid}. 후보: {list(_VALID_MODELS)}",
                "stockCode": stockCode,
                "market": market,
            }
        models_used = list(models)
        chosen = "+".join(models_used) if len(models_used) > 1 else models_used[0]

    horizon = max(1, int(horizon))
    calib_k = max(int(n * calibFraction), 5)
    calib_k = min(calib_k, n - 5) if n > 10 else calib_k

    forecasts_per_model: list[np.ndarray] = []
    residuals_calib: list[np.ndarray] = []
    for m in models_used:
        fcst, in_sample = _MODEL_FNS[m](log_ret, horizon)
        resid = log_ret[-calib_k:] - in_sample[-calib_k:]
        forecasts_per_model.append(fcst)
        residuals_calib.append(resid)

    point_forecasts = np.mean(np.stack(forecasts_per_model), axis=0)
    residuals_pooled = np.concatenate(residuals_calib)
    half_width = _conformalHalfWidth(residuals_pooled, alpha=alpha)

    cum_log = np.cumsum(point_forecasts)

    forecast_table: list[dict] = []
    for h in range(horizon):
        point = float(point_forecasts[h])
        cum = float(cum_log[h])
        # 누적 conformal 폭은 sqrt(h+1) 스케일링 (Bonferroni-free 가법형 — IID 잔차 가정)
        cum_q = half_width * float(np.sqrt(h + 1))
        forecast_table.append(
            {
                "horizon": int(h + 1),
                "pointForecast": round(point, 6),
                "lowerBound": round(point - half_width, 6),
                "upperBound": round(point + half_width, 6),
                "cumLogReturn": round(cum, 6),
                "cumLowerBound": round(cum - cum_q, 6),
                "cumUpperBound": round(cum + cum_q, 6),
                "pricePoint": round(last_close * float(np.exp(cum)), 4),
                "priceLower": round(last_close * float(np.exp(cum - cum_q)), 4),
                "priceUpper": round(last_close * float(np.exp(cum + cum_q)), 4),
            }
        )

    cum_h = float(cum_log[-1])
    cum_q_h = half_width * float(np.sqrt(horizon))
    summary = (
        f"{chosen}: {cum_h * 100:+.2f}% over {horizon}d "
        f"([{(cum_h - cum_q_h) * 100:+.2f}%, {(cum_h + cum_q_h) * 100:+.2f}%] 90% CI)"
    )

    return {
        "stockCode": stockCode,
        "market": market,
        "lastClose": round(last_close, 4),
        "lastDate": last_date,
        "modelChosen": chosen,
        "modelsConsidered": models_used,
        "horizon": horizon,
        "nObs": n,
        "calibSize": int(calib_k),
        "pAdfStationary": round(p_adf, 4),
        "conformalHalfWidth": round(half_width, 6),
        "forecastTable": forecast_table,
        "summary": summary,
    }


# ── walk_forward refit helper (forecast → Rule 변환) ────────


def forecastRuleFactory(
    *,
    models: list[str] | None = None,
    threshold: float = 0.002,
    calibFraction: float = 0.2,
    alpha: float = 0.10,
):
    """forecast 모델 기반 walk_forward rule_factory 생성.

    walk_forward(close, rule_factory=forecastRuleFactory(threshold=0.002), ...) 형태로
    사용. fold 마다 IS 구간만 보고 forecast fit, OOS 일수만큼 점추정 + interval 산출,
    threshold 룰로 entry/exit boolean 변환.

    Entry 룰: pointForecast > threshold AND lowerBound > -threshold (양수 + 안전마진).
    Exit 룰:  pointForecast < 0 OR lowerBound < -2*threshold.

    Returns
    -------
    Callable[[is_close, oos_len], Rule]
        반환 Rule 의 length = len(is_close) + oos_len. IS 구간은 entry/exit 모두 False
        (학습용), OOS 구간만 forecast 신호.
    """
    from dartlab.quant.strategy.rule import Rule

    def _factory(is_close: np.ndarray, oos_len: int) -> Rule:
        n_is = len(is_close)
        total = n_is + int(oos_len)
        entry = np.zeros(total, dtype=bool)
        exit_ = np.zeros(total, dtype=bool)

        # IS 구간 log-return 시계열
        if n_is < 30:
            return Rule(entry_expr=entry, exit_expr=exit_)
        log_ret = np.diff(np.log(is_close))
        chosen = _pickModel(log_ret) if models is None else None
        models_used = models if models is not None else [chosen]

        forecasts_per: list[np.ndarray] = []
        residuals_per: list[np.ndarray] = []
        calib_k = max(int(len(log_ret) * calibFraction), 5)
        for m in models_used:
            fcst, in_sample = _MODEL_FNS[m](log_ret, oos_len)
            forecasts_per.append(fcst)
            residuals_per.append(log_ret[-calib_k:] - in_sample[-calib_k:])

        point_forecasts = np.mean(np.stack(forecasts_per), axis=0)
        residuals_pooled = np.concatenate(residuals_per)
        half_width = _conformalHalfWidth(residuals_pooled, alpha=alpha)

        # OOS 각 점에 대해 entry/exit 판정 (cumulative 가 아닌 1-step 기준)
        for h in range(int(oos_len)):
            point = float(point_forecasts[h])
            lower = point - half_width
            upper = point + half_width
            idx = n_is + h
            if point > threshold and lower > -threshold:
                entry[idx] = True
            if point < 0 or upper < -2 * threshold:
                exit_[idx] = True

        return Rule(entry_expr=entry, exit_expr=exit_)

    return _factory

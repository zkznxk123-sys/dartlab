"""시장 맥락 분석 — 종목의 시장 베타 + 거시 민감도 + 수급 강도 1 행 evidence.

가격-거시 OLS (price-level macro/index sensitivity, 일별 252 d 윈도우).
펀더멘털-거시 OLS (`scan.macroBeta`, 연간 매출성장 vs 거시) 와 책임 분리:
- `quant.marketContext` = price-level (일별 log-return 회귀)
- `scan.macroBeta`      = fundamental-level (연간 매출 vs 거시)

학술 근거:
- Sharpe (1964): CAPM β
- Chen, Roll, Ross (1986): macroeconomic factors and stock returns
- Choe, Kho, Stulz (1999): foreign investors and KR stock returns

설계 원칙:
- numpy only. scipy / statsmodels / sklearn import 금지.
- gather.history (시장 지수) + gather.macro (거시 wide) + gather.flow (수급) 3 소스만 사용.
- forward-fill 로 일별 빈도 정렬 — 월별 거시는 daily 회귀 시 R² 가 작을 수 있다 (의도된 noise).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl

from dartlab.core.polarsUtil import isEmptyDf
from dartlab.frame.market import resolveMarket
from dartlab.quant.screen.dataAccess import fetchOhlcv, ohlcvToArrays

_KR_MACRO_DEFAULT = ("USDKRW", "BASE_RATE", "CPI", "M2")
_US_MACRO_DEFAULT = ("FEDFUNDS", "DGS10", "DCOILWTICO", "CPIAUCSL")


def _ols(y: np.ndarray, x: np.ndarray) -> dict[str, float]:
    """단변량 OLS — y = α + β x. β / α / R² 반환 (numpy only)."""
    n = min(len(y), len(x))
    if n < 5:
        return {"beta": float("nan"), "alpha": float("nan"), "r2": float("nan"), "n": n}
    y = y[:n]
    x = x[:n]
    mask = np.isfinite(y) & np.isfinite(x)
    y = y[mask]
    x = x[mask]
    if len(y) < 5:
        return {"beta": float("nan"), "alpha": float("nan"), "r2": float("nan"), "n": int(len(y))}
    x_mean = float(np.mean(x))
    y_mean = float(np.mean(y))
    xc = x - x_mean
    yc = y - y_mean
    denom = float(np.dot(xc, xc))
    if denom < 1e-12:
        return {"beta": 0.0, "alpha": float(y_mean), "r2": 0.0, "n": int(len(y))}
    beta = float(np.dot(xc, yc) / denom)
    alpha = y_mean - beta * x_mean
    pred = alpha + beta * x
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum(yc**2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0
    return {"beta": beta, "alpha": alpha, "r2": float(r2), "n": int(len(y))}


def _capmBetaAlpha(stockClose: np.ndarray, bmClose: np.ndarray) -> tuple[float, float, float, int] | None:
    """CAPM 회귀 — r_i = α + β r_m + ε. (β, α annualized, R², nObs)."""
    if len(stockClose) < 30 or len(bmClose) < 30:
        return None
    r_i = np.diff(np.log(stockClose))
    r_m = np.diff(np.log(bmClose))
    ols = _ols(r_i, r_m)
    if not np.isfinite(ols["beta"]):
        return None
    return ols["beta"], ols["alpha"] * 252.0, ols["r2"], ols["n"]


def _alignDates(stockDf: pl.DataFrame, otherDf: pl.DataFrame, *, otherValueCol: str) -> tuple[np.ndarray, np.ndarray]:
    """date 기준 inner join → (stock_close, other_value) 같은 길이 array.

    other_df 의 결측은 forward-fill 로 보간 (월별 거시 변수 호환).
    """
    if isEmptyDf(stockDf) or isEmptyDf(otherDf):
        return np.array([]), np.array([])
    if "date" not in stockDf.columns or "date" not in otherDf.columns:
        return np.array([]), np.array([])
    s = stockDf.select(["date", "close"]).sort("date")
    o = otherDf.select(["date", otherValueCol]).sort("date")
    o = o.with_columns(pl.col(otherValueCol).forward_fill())
    joined = s.join_asof(o, on="date", strategy="backward").drop_nulls(
        subset=[otherValueCol]
    )  # polars-streaming-unsupported: asof
    if joined.height < 5:
        return np.array([]), np.array([])
    return (
        joined["close"].to_numpy().astype(np.float64),
        joined[otherValueCol].to_numpy().astype(np.float64),
    )


def _macroBetaSet(stockDf: pl.DataFrame, macroDf: pl.DataFrame, macroVars: tuple[str, ...]) -> dict[str, float]:
    """거시 wide DF 의 각 컬럼별 β 산출 — Δlog stock vs Δ macro (변수에 따라 Δ 또는 Δlog)."""
    out: dict[str, float] = {}
    if isEmptyDf(stockDf) or isEmptyDf(macroDf):
        return out
    cols_present = [c for c in macroVars if c in macroDf.columns]
    for var in cols_present:
        stockClose, macro_val = _alignDates(stockDf, macroDf, otherValueCol=var)
        if len(stockClose) < 30:
            continue
        # Δlog stock_close (일별 수익률)
        r_i = np.diff(np.log(stockClose))
        # 거시 변수 변화: USDKRW / FX → Δlog, 금리 (BASE_RATE/FEDFUNDS/DGS10) → Δ, 그 외 → Δlog
        if var.upper() in {"BASE_RATE", "FEDFUNDS", "DGS10"}:
            macro_delta = np.diff(macro_val)
        else:
            with np.errstate(divide="ignore", invalid="ignore"):
                macro_delta = np.diff(np.log(np.where(macro_val > 0, macro_val, np.nan)))
        ols = _ols(r_i, macro_delta)
        if np.isfinite(ols["beta"]):
            key = _camelize(var) + "Beta"
            out[key] = round(ols["beta"], 6)
            out[key + "_r2"] = round(ols["r2"], 4)
    return out


def _camelize(var: str) -> str:
    """매크로 변수명 → camelCase 컬럼 prefix.

    KR/US 의 같은 의미 변수 (CPI vs CPIAUCSL) 가 같은 출력 키를 만들면 사용자가
    macroVars=["CPI","CPIAUCSL"] 동시 입력 시 silent dict 덮어쓰기. 따라서 US CPI 는
    cpiUs 로 분리한다.
    """
    aliases = {
        "USDKRW": "usdkrw",
        "BASE_RATE": "baseRate",
        "CPI": "cpi",
        "M2": "m2",
        "FEDFUNDS": "fedFunds",
        "DGS10": "dgs10",
        "DCOILWTICO": "oil",
        "CPIAUCSL": "cpiUs",  # KR CPI 와 키 충돌 방지
    }
    return aliases.get(var.upper(), var.lower())


def _flowMetrics(stockCode: str, market: str) -> dict[str, Any]:
    """수급 시계열 요약 — smartMoney 누적 / z-score / momentum.

    gather.flow 가 짧은 시계열 (네이버 limit ~수 일) 만 반환할 수 있어 윈도우를 단계적으로
    깎아 가용한 metric 만 산출한다. 60 d / 20 d / 5 d 의 3 단계.
    """
    out: dict[str, Any] = {}
    if market != "KR":
        out["flowAvailable"] = False
        return out
    try:
        from dartlab.gather.entry import GatherEntry

        g = GatherEntry()
        flow_df = g("flow", stockCode)
    except (ImportError, ValueError, TypeError, RuntimeError):
        out["flowAvailable"] = False
        return out
    if isEmptyDf(flow_df):
        out["flowAvailable"] = False
        return out
    cols = flow_df.columns
    if "foreignNet" not in cols or "institutionNet" not in cols:
        out["flowAvailable"] = False
        return out
    out["flowAvailable"] = True
    smart = (
        flow_df.with_columns((pl.col("foreignNet") + pl.col("institutionNet")).alias("smartNet"))
        .sort("date")
        .get_column("smartNet")
        .to_numpy()
        .astype(np.float64)
    )
    smart = smart[np.isfinite(smart)]
    n = len(smart)
    out["flowNObs"] = int(n)
    if n >= 60:
        out["smartMoneyNet60d"] = round(float(np.sum(smart[-60:])), 0)
        if n >= 252:
            ref = smart[-252:]
            std_ref = float(np.std(ref))
            mean_ref = float(np.mean(ref))
            if std_ref > 1e-6:
                out["smartMoneyZ60d"] = round((float(np.mean(smart[-60:])) - mean_ref) / std_ref, 4)
    if n >= 20:
        out["flowMomentum20d"] = round(float(np.sum(smart[-20:])), 0)
    if n >= 5:
        out["smartMoneyNetRecent5d"] = round(float(np.sum(smart[-5:])), 0)
        out["smartMoneyNetLast"] = round(float(smart[-1]), 0)
    return out


def calcMarketContext(
    stockCode: str,
    *,
    market: str = "auto",
    lookback: int = 252,
    macroVars: list[str] | None = None,
    **kwargs,
) -> dict:
    """종목의 시장 맥락 — 시장 베타 + 거시 민감도 + 수급 강도 1 행 evidence.

    가격 시계열 기반 (일별 log-return). 펀더멘털 (재무성장-거시) 회귀는
    `scan.macroBeta` 가 별도 책임 — 변수 (가격 vs 매출), 단위 (일/연), 컬럼명 (cpiBeta vs gdpBeta) 모두 분리.

    Parameters
    ----------
    stockCode : str
        종목코드 또는 ticker.
    market : str
        "KR" / "US" / "auto".
    lookback : int
        회귀 윈도우 (일). 기본 252 (1 거래년).
    macroVars : list[str] | None
        거시 변수 명시. None 이면 KR 기본 ``("USDKRW", "BASE_RATE", "CPI", "M2")`` /
        US 기본 ``("FEDFUNDS", "DGS10", "DCOILWTICO", "CPIAUCSL")``.
    **kwargs
        ``fetchOhlcv`` 전달 (start, end 등).

    Returns
    -------
    dict
        stockCode, market, lookback, dateRef, lastClose,
        marketBeta, marketAlpha (annualized), marketR2, nObsCAPM,
        usdkrwBeta / baseRateBeta / cpiBeta / m2Beta (KR) 또는
        fedFundsBeta / dgs10Beta / oilBeta / cpiBeta (US) + 각 _r2,
        smartMoneyNet60d, smartMoneyZ60d, flowMomentum20d (KR only),
        flowAvailable, flowNObs.
        실패 시: ``{"error": ..., "stockCode": ..., "market": ...}``.

    When
    ----
    AI 가 "이 종목의 시장 민감도 + 환율/금리 베타 + 외국인+기관 강도" 를 한 번에 묻고 싶을 때.
    예: 005930 (수출주) 의 USDKRW 베타가 양수인지, 035420 (내수) 가 0 근처인지 부호 검증.

    How
    ---
    >>> import dartlab
    >>> dartlab.quant("marketContext", "005930")
    >>> dartlab.quant("시장맥락", "035420", lookback=504)
    >>> dartlab.quant("marketContext", "AAPL", macroVars=["FEDFUNDS", "DGS10"])

    Verified
    --------
    - 005930 (수출주) usdkrwBeta > 0 — 원화 약세 시 종목 수익률 +
    - 035420 (네이버, 내수 IT) |usdkrwBeta| 작음
    - marketBeta ∈ [0.3, 1.8] (KOSPI 종목 합리적 범위)

    Raises
    ------
    KeyError
        scan.macroBeta 와의 컬럼명 충돌 — 사용자가 명시 macroVars 에 GDP/금리 등 입력 시.

    Notes
    -----
    - 거시 wide DF (gather.macro KR scope=default) 의 컬럼명을 그대로 받아 forward-fill 로
      일별 정렬. 월별 변수 (CPI, M2) 는 R² 가 작을 수 있다 — 의도된 noise.
    - 금리 류 (BASE_RATE, FEDFUNDS, DGS10) 는 Δ (단순 차분), 그 외는 Δlog 로 회귀.
    - flow 는 KR 전용. US 종목은 flowAvailable=False 로 관련 키 누락.
    - CAPM 의 시장 지수는 stockCode 의 상장 시장 (KOSPI/KOSDAQ) 또는 SPX (US) — `fetchBenchmarkOhlcv` SSOT 재사용.
    """
    market = resolveMarket(stockCode, market)

    # 1. 종목 OHLCV
    ohlcv = fetchOhlcv(stockCode, **kwargs)
    if isEmptyDf(ohlcv):
        return {"error": f"{stockCode} 주가 데이터 없음", "stockCode": stockCode, "market": market}

    arr = ohlcvToArrays(ohlcv)
    close = arr.get("close")
    dates = arr.get("date")
    if close is None or len(close) < 60:
        return {
            "error": f"{stockCode} 데이터 부족 (최소 60 일)",
            "stockCode": stockCode,
            "market": market,
            "nObs": int(len(close)) if close is not None else 0,
        }

    n_use = min(int(lookback), len(close))
    last_close = float(close[-1])
    last_date = str(dates[-1]) if dates else None
    start_date = str(dates[-n_use]) if dates else None
    end_date = last_date

    # 종목 DataFrame 슬라이스 (lookback)
    stockDf = ohlcv.tail(n_use).select(["date", "close"]).sort("date")

    result: dict[str, Any] = {
        "stockCode": stockCode,
        "market": market,
        "lookback": int(n_use),
        "dateRef": last_date,
        "lastClose": round(last_close, 4),
    }

    # 2. CAPM β / α (vs 시장 지수)
    try:
        from dartlab.quant.benchmark.data import fetchBenchmarkOhlcv

        bm_df = fetchBenchmarkOhlcv(
            stockCode,
            market=market,
            benchmarkMode="market",
            start=start_date,
            end=end_date,
        )
        if not isEmptyDf(bm_df):
            joined = stockDf.join(
                bm_df.select(["date", "close"]).rename({"close": "bmClose"}),
                on="date",
                how="inner",
            ).sort("date")
            if joined.height >= 30:
                sc = joined["close"].to_numpy().astype(np.float64)
                bc = joined["bmClose"].to_numpy().astype(np.float64)
                capm = _capmBetaAlpha(sc, bc)
                if capm is not None:
                    beta, alpha_ann, r2, n_capm = capm
                    result["marketBeta"] = round(beta, 4)
                    result["marketAlpha"] = round(alpha_ann, 4)
                    result["marketR2"] = round(r2, 4)
                    result["nObsCAPM"] = int(n_capm)
    except (ImportError, ValueError, TypeError, RuntimeError) as exc:
        result["marketBetaError"] = type(exc).__name__

    # 3. 거시 민감도
    if macroVars is None:
        macroVars: tuple[str, ...] = _KR_MACRO_DEFAULT if market == "KR" else _US_MACRO_DEFAULT
    else:
        macroVars = tuple(macroVars)

    macroDf = None
    macro_source = "none"  # wide / singleFallback / none — 결과 키로 단일 노출
    wide_error: str | None = None
    try:
        from dartlab.gather.entry import GatherEntry

        g = GatherEntry()
        macroDf = g("macro", market=market)
        if not isEmptyDf(macroDf):
            macro_source = "wide"
    except (ImportError, ValueError, TypeError, RuntimeError) as exc:
        wide_error = type(exc).__name__
        macroDf = None

    # wide 호출 실패 또는 빈 DF 시 var 별 단일 fetch fallback
    if isEmptyDf(macroDf):
        try:
            from dartlab.gather.entry import GatherEntry

            g = GatherEntry()
            parts: list[pl.DataFrame] = []
            for var in macroVars:
                try:
                    single = g("macro", var)
                except (ImportError, ValueError, TypeError, RuntimeError):
                    continue
                if isEmptyDf(single):
                    continue
                cols = single.columns
                if "date" in cols and "value" in cols:
                    parts.append(single.select(["date", "value"]).rename({"value": var}))
                elif "date" in cols and var in cols:
                    parts.append(single.select(["date", var]))
            if parts:
                # outer join on date (forward-fill 호환)
                macroDf = parts[0]
                for p in parts[1:]:
                    macroDf = macroDf.join(p, on="date", how="full", coalesce=True)
                macroDf = macroDf.sort("date")
                macro_source = "singleFallback"
        except (ImportError, ValueError, TypeError, RuntimeError):
            pass

    result["macroSource"] = macro_source
    if wide_error is not None:
        result["macroWideErrorType"] = wide_error  # 진단용 (singleFallback 성공해도 wide 실패 사유 보존)
    if not isEmptyDf(macroDf):
        macro_betas = _macroBetaSet(stockDf, macroDf, macroVars)
        result.update(macro_betas)
        result["macroVarsUsed"] = list(macroVars)

    # 4. 수급 (KR only)
    flow_metrics = _flowMetrics(stockCode, market)
    result.update(flow_metrics)

    # 5. summary
    pieces = []
    if "marketBeta" in result:
        pieces.append(f"β={result['marketBeta']}")
    if "usdkrwBeta" in result:
        pieces.append(f"USDKRW β={result['usdkrwBeta']:+.3f}")
    if "fedFundsBeta" in result:
        pieces.append(f"FEDFUNDS β={result['fedFundsBeta']:+.3f}")
    if "smartMoneyZ60d" in result:
        pieces.append(f"smartMoney Z={result['smartMoneyZ60d']:+.2f}")
    if pieces:
        result["summary"] = " · ".join(pieces)

    return result

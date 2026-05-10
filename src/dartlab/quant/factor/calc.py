"""팩터 분해 — book-based 횡단면 SMB/HML/RMW/CMA로 회귀.

학술 근거:
- Fama & French (2015): 5-factor model (MKT, SMB, HML, RMW, CMA)
- Hou, Xue, Zhang (2015): q-factor model (별도 구현 예정, 현재는 FF5만)
- Grinold & Kahn (2000), *Active Portfolio Management* Ch.5-7:
  Information Ratio (알파/추적오차) + Fundamental Law + Residual Risk. 팩터 제거
  후 잔여 수익 시계열을 IR 원료로 사용한다.
  IR/Fundamental Law: `quant/strategy/metrics.py`.
  Residual Risk Decomposition: 이 파일 하단 (quant 엔진 내부).

데이터 흐름:
1. factorBuild.buildFactors(market) — scan finance.parquet에서 5분위 포트폴리오
   구성, 동일가중 평균 일별 log return → SMB/HML/RMW/CMA 시계열
2. decomposeFactor — 단일 종목 vs (MKT + 빌드된 팩터) 다변수 OLS

이전 버전(2026-04-06 이전)은 변동성 합성 가짜 프록시를 사용했고 audit에서 진짜
SMB와 음의 상관(−0.51)이 발견됨. 이번 재구현으로 폐기. 자세한 내용은
data/dart/auditQuant/factor.md 참조.

⚠️ 한계:
- size proxy = book equity (시가총액 데이터 미수집). 시총 인프라 추가 후 진짜 시총으로 교체.
- BM proxy = equity/assets. 시총 부재로 진짜 BM 불가.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from dartlab.core.polarsUtil import isEmptyDf
from dartlab.quant.screen.dataAccess import fetchOhlcv, ohlcvToArrays, resolve_market
from dartlab.quant.strategy.metrics import TRADING_DAYS, calcIR, fundamentalLawIR

log = logging.getLogger(__name__)


def decomposeFactor(stockCode: str, *, market: str = "auto", **kwargs: Any) -> dict:
    """진짜 횡단면 팩터 시계열로 단일 종목 회귀.

    Args:
        stockCode: 종목코드 또는 ticker.
        market: "KR" | "US" | "auto".

    Returns:
        dict — MKT/SMB/HML/RMW/CMA 로딩 + alpha + R² + 데이터 적정성 + 한계 명시
        + Grinold/Kahn IR 지표 (informationRatio raw, informationRatioAnnualized,
        expectedIR via Fundamental Law).
    """
    market = resolve_market(stockCode, market)
    benchmark = kwargs.pop("benchmark", None)
    benchmarkMode = kwargs.pop("benchmarkMode", "market")

    ohlcv = fetchOhlcv(stockCode, **kwargs)
    if isEmptyDf(ohlcv):
        return {"error": f"{stockCode} 주가 데이터 없음"}
    arr = ohlcvToArrays(ohlcv)
    close = arr.get("close")
    if close is None or len(close) < 60:
        return {"error": f"{stockCode} 데이터 부족 (최소 60일)"}
    stockRet = np.diff(np.log(close))

    from dartlab.quant.benchmark.data import fetchBenchmarkOhlcv

    bench, benchmark_meta = fetchBenchmarkOhlcv(
        stockCode,
        market=market,
        benchmark=benchmark,
        benchmarkMode=benchmarkMode,
        start=kwargs.get("start"),
        end=kwargs.get("end"),
        returnMeta=True,
    )
    if isEmptyDf(bench):
        return {"error": "벤치마크 데이터 없음"}
    bench_close = ohlcvToArrays(bench).get("close")
    if bench_close is None:
        return {"error": "벤치마크 close 없음"}
    benchRet = np.diff(np.log(bench_close))

    # 진짜 횡단면 팩터 시계열 빌드/로드
    if market == "KR":
        from dartlab.quant.factor.build import buildFactors

        factors = buildFactors(market)
    else:
        factors = None  # US는 후순위

    if factors is None:
        # fallback: 1-factor CAPM (MKT만)
        out = _capmFallback(stockCode, market, stockRet, benchRet)
        if "error" not in out:
            out["benchmarkUsed"] = benchmark_meta
        return out

    smb = factors["smb"]
    hml = factors["hml"]
    rmw = factors.get("rmw")
    cma = factors.get("cma")

    # 길이 정렬
    ml = min(len(stockRet), len(benchRet), len(smb), len(hml))
    if rmw is not None:
        ml = min(ml, len(rmw))
    if cma is not None:
        ml = min(ml, len(cma))
    if ml < 30:
        return {"error": f"공통 기간 부족 ({ml}일)"}

    y = stockRet[-ml:]
    cols = [benchRet[-ml:], smb[-ml:], hml[-ml:]]
    names = ["MKT", "SMB", "HML"]
    if rmw is not None:
        cols.append(rmw[-ml:])
        names.append("RMW")
    if cma is not None:
        cols.append(cma[-ml:])
        names.append("CMA")

    X = np.column_stack(cols)
    betas, alpha_val, r2, t_stats, residuals = _multiOls(y, X)

    # Grinold/Kahn Ch.5 — raw IR = mean(residual alpha) / std(residual alpha)
    # residuals 는 팩터 제거 후 잔여 일별 수익 (raw 알파 시계열)
    rawIR = calcIR(residuals) if residuals is not None else float("nan")
    annualizedIR = float(rawIR * np.sqrt(252)) if not np.isnan(rawIR) else float("nan")
    # Fundamental Law 이론 IR (raw IR 을 연간 breadth=252 독립 관측으로 취급할 때의 기대치)
    expectedIR = fundamentalLawIR(rawIR, 252) if not np.isnan(rawIR) else float("nan")

    # Grinold Ch.7 — systematic / residual risk 분해
    riskDecomp = decomposeRisk(
        returns=y,
        factorExposures=betas,
        factorReturns=X,
        annualize=True,
    )
    # residual α series IR (연환산 포함)
    resAlpha = residualAlphaIR(residuals) if residuals is not None else None

    result: dict = {
        "stockCode": stockCode,
        "market": market,
        "model": f"FF{len(names)}-real" if rmw is not None and cma is not None else f"FF{len(names)}",
        "dataPoints": int(ml),
        "dataAdequacy": "low" if ml < 252 else "ok",
        "alpha": round(float(alpha_val * 252), 4),
        "rSquared": round(float(r2), 4),
        "informationRatio": round(float(rawIR), 4) if not np.isnan(rawIR) else None,
        "informationRatioAnnualized": round(float(annualizedIR), 4) if not np.isnan(annualizedIR) else None,
        "expectedIR": round(float(expectedIR), 4) if not np.isnan(expectedIR) else None,
        # Grinold Ch.7 — risk decomposition
        "systematicRisk": round(float(riskDecomp["systematicRisk"]), 4),
        "residualRisk": round(float(riskDecomp["residualRisk"]), 4),
        "totalRisk": round(float(riskDecomp["totalRisk"]), 4),
        "systematicShare": round(float(riskDecomp["systematicShare"]), 4),
        "residualShare": round(float(riskDecomp["residualShare"]), 4),
        "trackingError": round(float(riskDecomp["trackingError"]), 4),
        # residual alpha stats
        "alphaAnnual": round(float(resAlpha["alpha"]), 4) if resAlpha else None,
        "factorYear": factors["year"],
        "factorUniverse": factors["universe"],
        "factorNotes": factors.get("notes"),
        "benchmarkUsed": benchmark_meta,
    }

    for i, name in enumerate(names):
        result[name] = {
            "loading": round(float(betas[i]), 4),
            "tstat": round(float(t_stats[i]), 2) if t_stats is not None else None,
        }

    # 팩터 기여도 (연환산)
    contributions = {}
    for i, name in enumerate(names):
        contributions[name] = round(float(betas[i] * np.mean(X[:, i]) * 252), 4)
    result["contributions"] = contributions

    result["interpretation"] = _interpret(result, names)

    return result


def factorExposureLimits(loadings: dict, *, limits: dict | None = None) -> dict:
    """팩터 익스포저 한도 체크 (책 7장 — 팩터 리스크 관리).

    Args:
        loadings: {factor_name: loading_value} (decomposeFactor 결과의 항목)
        limits: {factor_name: max_abs}. None이면 기본값 사용.

    Returns:
        dict — 각 팩터의 |loading|, 한도 초과 여부, 권장 헤지비율.
    """
    if limits is None:
        # 기본: MKT 1.5, 나머지 0.5 (보수적)
        limits = {"MKT": 1.5, "SMB": 0.5, "HML": 0.5, "RMW": 0.5, "CMA": 0.5}

    breaches = []
    for name, lim in limits.items():
        info = loadings.get(name)
        if not isinstance(info, dict):
            continue
        ld = float(info.get("loading", 0))
        if abs(ld) > lim:
            # 헤지: 초과분만큼 반대 방향
            hedge_size = -(ld - np.sign(ld) * lim)
            breaches.append(
                {
                    "factor": name,
                    "loading": ld,
                    "limit": lim,
                    "excess": round(ld - np.sign(ld) * lim, 4),
                    "hedgeSize": round(float(hedge_size), 4),
                }
            )

    return {"limits": limits, "breaches": breaches, "compliant": len(breaches) == 0}


def hedgeRatio(targetLoading: float, hedgeLoading: float) -> float:
    """단일 팩터 헤지비율 — target / hedge.

    예: 포트의 SMB loading +0.8을 헤지하려면 SMB-vehicle의 SMB loading이
    +1.0인 경우 hedgeRatio = -0.8 (포트 1당 hedge -0.8).
    """
    if hedgeLoading == 0:
        return 0.0
    return float(-targetLoading / hedgeLoading)


# ══════════════════════════════════════════════════════════════════════
# Grinold Ch.7 — Residual Risk Model
# ══════════════════════════════════════════════════════════════════════
#
#     Total risk² = Systematic risk² + Residual risk²
#
# systematic = factor exposure 에서 오는 리스크 (hedgeable)
# residual = 종목 고유 (idiosyncratic). IR 의 분모 = tracking error.


def decomposeRisk(
    *,
    returns: np.ndarray,
    factorExposures: np.ndarray,
    factorReturns: np.ndarray,
    annualize: bool = True,
) -> dict:
    """Grinold Ch.7 — systematic / residual 리스크 분해.

    Returns
    -------
    dict with systematicRisk, residualRisk, totalRisk, systematicShare,
    residualShare, trackingError (= residualRisk; IR 분모).
    """
    y = np.asarray(returns, dtype=float)
    beta = np.asarray(factorExposures, dtype=float)
    F = np.asarray(factorReturns, dtype=float)
    if F.ndim == 1:
        F = F.reshape(-1, 1)
    if y.size < 2 or F.shape[0] != y.size:
        return {
            "systematicRisk": float("nan"),
            "residualRisk": float("nan"),
            "totalRisk": float("nan"),
            "systematicShare": float("nan"),
            "residualShare": float("nan"),
            "trackingError": float("nan"),
        }
    sys_series = F @ beta
    residual = y - sys_series
    sys_var = float(np.var(sys_series, ddof=1))
    res_var = float(np.var(residual, ddof=1))
    total_var = sys_var + res_var
    scale = np.sqrt(TRADING_DAYS) if annualize else 1.0
    sys_risk = float(np.sqrt(max(sys_var, 0.0)) * scale)
    res_risk = float(np.sqrt(max(res_var, 0.0)) * scale)
    total_risk = float(np.sqrt(max(total_var, 0.0)) * scale)
    sysShare = float(sys_var / total_var) if total_var > 0 else float("nan")
    res_share = 1.0 - sysShare if not np.isnan(sysShare) else float("nan")
    return {
        "systematicRisk": sys_risk,
        "residualRisk": res_risk,
        "totalRisk": total_risk,
        "systematicShare": sysShare,
        "residualShare": res_share,
        "trackingError": res_risk,
    }


def residualRiskForecast(
    historicalResidual: np.ndarray,
    horizonDays: int = 252,
    halfLifeDays: int = 60,
) -> float:
    """EWMA 기반 잔여 변동성 예측 (Grinold Ch.7 권고).

    Parameters
    ----------
    historicalResidual : np.ndarray
        팩터 제거 후 잔여 일별 수익률 시계열.
    horizonDays : int
        예측 기간 (일). 기본 252 (1년).
    halfLifeDays : int
        EWMA 반감기 (일). 기본 60.

    Returns
    -------
    float
        horizonDays 기간의 잔여 변동성 예측치 (%). 표본 < 10 이면 NaN.
    """
    r = np.asarray(historicalResidual, dtype=float)
    r = r[~np.isnan(r)]
    if r.size < 10:
        return float("nan")
    lam = 0.5 ** (1.0 / halfLifeDays)
    weights = lam ** np.arange(r.size - 1, -1, -1)
    weights /= weights.sum()
    mu = float(np.sum(weights * r))
    var = float(np.sum(weights * (r - mu) ** 2))
    return float(np.sqrt(var * horizonDays))


def residualAlphaIR(residualSeries: np.ndarray, *, annualize: bool = True) -> dict:
    """Grinold 잔여 시계열로부터 raw IR + 연환산 alpha/trackingError.

    Parameters
    ----------
    residualSeries : np.ndarray
        팩터 제거 후 잔여 일별 수익률 시계열.
    annualize : bool
        True 면 252 거래일 기준 연환산. 기본 True.

    Returns
    -------
    dict
        rawIR : float — 일별 IR = mean/std (배)
        annualizedIR : float | None — 연환산 IR (배). annualize=False 시 None
        alpha : float — 잔여 알파 (%, 연환산 시 ×252)
        trackingError : float — 추적오차 = std × √252 (%)
    """
    r = np.asarray(residualSeries, dtype=float)
    r = r[~np.isnan(r)]
    if r.size < 2:
        return {
            "rawIR": float("nan"),
            "annualizedIR": None,
            "alpha": float("nan"),
            "trackingError": float("nan"),
        }
    mu = float(r.mean())
    sd = float(r.std(ddof=1))
    raw_ir = mu / sd if sd > 0 else 0.0
    scale = np.sqrt(TRADING_DAYS) if annualize else 1.0
    return {
        "rawIR": float(raw_ir),
        "annualizedIR": float(raw_ir * np.sqrt(TRADING_DAYS)) if annualize else None,
        "alpha": float(mu * TRADING_DAYS) if annualize else float(mu),
        "trackingError": float(sd * scale),
    }


def _capmFallback(stockCode: str, market: str, sr: np.ndarray, br: np.ndarray) -> dict:
    """팩터 빌드 실패 시 1-factor CAPM."""
    ml = min(len(sr), len(br))
    if ml < 30:
        return {"error": "공통 기간 부족"}
    y = sr[-ml:]
    x = br[-ml:]
    cov = float(np.cov(y, x, ddof=1)[0, 1])
    var = float(np.var(x, ddof=1))
    beta = cov / var if var > 0 else 0
    alpha = float(np.mean(y) - beta * np.mean(x))
    yhat = alpha + beta * x
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    return {
        "stockCode": stockCode,
        "market": market,
        "model": "CAPM-fallback",
        "info": "factorBuild 실패 → 1-factor CAPM으로 fallback",
        "dataPoints": int(ml),
        "MKT": {"loading": round(beta, 4), "tstat": None},
        "alpha": round(alpha * 252, 4),
        "rSquared": round(r2, 4),
    }


def _multiOls(y, X):
    """다변수 OLS + t-stats + residuals.

    Returns:
        (betas, alpha, r2, t_stats, residuals). residuals 는 알파 시계열
        (팩터 제거 후 잔여 일별 수익). IR 계산의 원료.
    """
    n, k = X.shape
    X_aug = np.column_stack([np.ones(n), X])
    try:
        beta = np.linalg.lstsq(X_aug, y, rcond=None)[0]
        y_hat = X_aug @ beta
        resid = y - y_hat
        ss_res = float(np.sum(resid**2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        t_stats = None
        if n > k + 1:
            mse = ss_res / (n - k - 1)
            try:
                cov = mse * np.linalg.inv(X_aug.T @ X_aug)
                se = np.sqrt(np.diag(cov))
                t_stats = beta / se
                t_stats = t_stats[1:]
            except np.linalg.LinAlgError:
                pass

        return beta[1:], float(beta[0]), r2, t_stats, resid
    except np.linalg.LinAlgError:
        return np.zeros(k), 0.0, 0.0, None, None


def _interpret(result: dict, names: list[str]) -> list[str]:
    interp = []
    for name in names:
        info = result.get(name)
        if not isinstance(info, dict):
            continue
        ld = info.get("loading", 0)
        ts = info.get("tstat")
        sig = ts is not None and abs(ts) > 2.0

        if name == "MKT":
            if ld > 1.2:
                interp.append(f"공격적 시장 민감도 (β={ld:.2f})")
            elif ld < 0.8:
                interp.append(f"방어적 (β={ld:.2f})")
        elif sig:
            labels = {
                "SMB": ("소형주 특성", "대형주 특성"),
                "HML": ("고BM(가치)", "저BM(성장)"),
                "RMW": ("고수익성(profitable)", "저수익성(weak)"),
                "CMA": ("보수적 투자(conservative)", "공격적 투자(aggressive)"),
            }
            pos, neg = labels.get(name, ("양", "음"))
            interp.append(pos if ld > 0 else neg)

    return interp


# ══════════════════════════════════════════════════════════════════════
# Phase B0 — Alphalens-style Factor Tear Sheet (story 시장분석 섹션)
# ══════════════════════════════════════════════════════════════════════


def calcFactorTearSheet(
    factorName: str = "smb",
    *,
    market: str = "KR",
) -> dict | None:
    """팩터 tear sheet — long-short 시계열의 Sharpe / 누적수익 / MDD / Win Rate (Alphalens 표준).

    Capabilities:
        - 4 표준 Fama-French 팩터 (smb / hml / rmw / cma) 의 정량 평가 metric
        - Long-short 일별 시계열 (factorBuild.buildFactors) 기반
        - 연환산 수익 / 변동성 / Sharpe / 누적수익 / Win Rate / Max Drawdown
        - 실/proxy 구분 (isRealFamaFrench) 노출 — KRX 시총 직접 vs book proxy

    AIContext:
        - story 6막-3 시장분석 섹션이 자동 호출 (`factorTearSheetBlock`)
        - 4 팩터 동시 평가로 한국 시장 알파 원천 정량화
        - Sharpe > 1.0 = 강한 alpha, > 0.5 = 약한 alpha, < 0 = 역방향

    Guide:
        - "size 팩터 평가" → calcFactorTearSheet("smb")
        - "value 팩터" → calcFactorTearSheet("hml")
        - "quality 팩터" → calcFactorTearSheet("rmw")
        - "investment 팩터" → calcFactorTearSheet("cma")

    SeeAlso:
        - factorBuild.buildFactors : SMB/HML/RMW/CMA 시계열 빌드
        - decomposeFactor : 단일 종목 FF5 회귀 (loadings)
        - calcStrategySnapshot : 8 검증 스타일 백테스트

    Args:
        factorName: ``"smb"`` | ``"hml"`` | ``"rmw"`` | ``"cma"`` (대소문자 무관). 기본 ``"smb"``.
        market: ``"KR"`` | ``"US"``. 기본 ``"KR"``.

    Returns:
        dict
            factorName : str — 팩터명 (대문자, 예: "SMB")
            market : str — "KR" / "US"
            year : str — fundamental 기준 연도
            universe : int — 종목 수
            nObs : int — 일별 시계열 관측 수 (거래일)
            longShortAnnualReturn : float — Long-short 연환산 수익 (%)
            longShortAnnualVol : float — 연환산 변동성 (%)
            longShortSharpe : float — Sharpe ratio (배, mean/std × √252)
            longShortCumReturn : float — 누적 수익 (%, 전기간)
            longShortWinRate : float — 양수 일자 비율 (%)
            maxDrawdown : float — 최대낙폭 (%, 음수)
            sizeSource : str — "KRX_MKTCAP" 또는 "book_equity_proxy"
            bmSource : str — "equity/marketCap" 또는 "equity/assets_proxy"
            isRealFamaFrench : bool — KRX 시총 기반 진짜 FF 인지
            highN : int | None — Long 종목 수 (HML 의 경우 high-BM, 그 외 N/A)
            lowN : int | None — Short 종목 수
            interpretation : str — 정성 평가 ("강한 alpha (소형주 프리미엄)" 등)
            notes : str — 데이터 source 안내

    Examples:
        >>> from dartlab.quant.factor.calc import calcFactorTearSheet
        >>> ts = calcFactorTearSheet("smb")
        >>> print(ts["longShortSharpe"], ts["interpretation"])
        0.85 약한 alpha (소형주 프리미엄)

    Notes:
        - Alphalens-style 표준 metric. 단 Cross-sectional IC (mean / std / IR) 는 별도 트랙
          (현재는 long-short 기반 단순 metric — 후속 강화).
        - Sharpe 는 risk-free 0 가정 (한국 시장 단기 RF 무시).
        - Max Drawdown 은 누적 (1+r) 시계열의 peak-to-trough.
        - factorBuild.buildFactors() 가 캐시 → 같은 세션 재호출 빠름.
    """
    fname = factorName.lower().strip()
    if fname not in {"smb", "hml", "rmw", "cma"}:
        raise ValueError(f"factorName 알 수 없음: {factorName!r} — 허용: smb, hml, rmw, cma")

    from dartlab.quant.factor.build import buildFactors

    fb = buildFactors(market)
    if fb is None:
        return None
    arr = fb.get(fname)
    if arr is None or len(arr) < 30:
        return None

    arr = np.asarray(arr, dtype=np.float64)
    arr = arr[~np.isnan(arr)]
    if len(arr) < 30:
        return None

    annualMean = float(np.mean(arr) * 252) * 100
    annualStd = float(np.std(arr, ddof=1) * np.sqrt(252)) * 100
    sharpe = annualMean / annualStd if annualStd > 0 else 0.0
    cumReturn = float(np.exp(np.sum(arr)) - 1) * 100
    winRate = float(np.mean(arr > 0)) * 100

    # Max Drawdown
    cum = np.cumprod(1 + arr)
    peak = np.maximum.accumulate(cum)
    dd = (cum - peak) / peak
    maxDD = float(np.min(dd)) * 100

    # 종목 수 — 팩터별 다름
    longN = lowN = None
    if fname == "smb":
        longN, lowN = fb.get("smallN"), fb.get("bigN")
    elif fname == "hml":
        longN, lowN = fb.get("highBmN"), fb.get("lowBmN")

    return {
        "factorName": fname.upper(),
        "market": market,
        "year": fb.get("year"),
        "universe": fb.get("universe"),
        "nObs": int(len(arr)),
        "longShortAnnualReturn": round(annualMean, 2),
        "longShortAnnualVol": round(annualStd, 2),
        "longShortSharpe": round(sharpe, 2),
        "longShortCumReturn": round(cumReturn, 2),
        "longShortWinRate": round(winRate, 2),
        "maxDrawdown": round(maxDD, 2),
        "sizeSource": fb.get("sizeSource"),
        "bmSource": fb.get("bmSource"),
        "isRealFamaFrench": bool(fb.get("isRealFamaFrench", False)),
        "highN": longN,
        "lowN": lowN,
        "interpretation": _interpretFactorSharpe(sharpe, fname),
        "notes": fb.get("notes", ""),
    }


def _interpretFactorSharpe(sharpe: float, factor: str) -> str:
    """Sharpe ratio + 팩터 방향 → 정성 평가 한 줄."""
    if sharpe > 1.5:
        level = "매우 강한 alpha"
    elif sharpe > 1.0:
        level = "강한 alpha"
    elif sharpe > 0.5:
        level = "약한 alpha"
    elif sharpe > 0:
        level = "유의미하지 않음"
    elif sharpe > -0.5:
        level = "역방향 약함"
    else:
        level = "역방향 강함"

    direction_map = {
        "smb": ("소형주 프리미엄", "대형주 프리미엄"),
        "hml": ("가치주 프리미엄", "성장주 프리미엄"),
        "rmw": ("고수익성 프리미엄", "저수익성 프리미엄"),
        "cma": ("보수적 투자 프리미엄", "공격적 투자 프리미엄"),
    }
    pos, neg = direction_map.get(factor, (f"{factor.upper()} 프리미엄", f"{factor.upper()} 역방향"))
    direction = pos if sharpe > 0 else neg
    return f"{level} ({direction})"


def calcMultiFactorRisk(stockCode: str, *, market: str = "auto") -> dict | None:
    """Multi-Factor Risk Decomposition (Barra-style B Σ_f Bᵀ + D).

    Capabilities:
        - 단일 종목의 systematic vs idiosyncratic risk 분해
        - 4 팩터 (SMB/HML/RMW/CMA) 공분산 + 종목 노출 (B = decomposeFactor loadings)
        - 팩터별 리스크 기여도 (% of systematic)
        - 정성 평가 (팩터 의존도 + 최대 기여 팩터)

    AIContext:
        - story 시장분석 섹션의 ``riskDecompositionBlock`` 가 자동 호출
        - "총 리스크 30% 중 systematic 22% / idiosyncratic 8%, SMB 기여 +45%" 같은 정량
        - Barra MSCI 의 multi-factor risk model 표준 (B Σ_f Bᵀ + D)

    SeeAlso:
        - decomposeFactor : 종목의 팩터 loadings (B)
        - factorBuild.buildFactors : SMB/HML/RMW/CMA 시계열 (Σ_f 원료)
        - calcFactorTearSheet : 팩터별 long-short Sharpe 평가

    Args:
        stockCode: 종목코드 또는 ticker.
        market: ``"KR"`` | ``"US"`` | ``"auto"``.

    Returns:
        dict
            stockCode : str
            market : str
            model : str — "Barra-style FF4 Multi-Factor"
            systematicRisk : float — 팩터 기여 리스크 (연환산 %)
            residualRisk : float — 종목 고유 리스크 (idiosyncratic, 연환산 %)
            totalRisk : float — 합산 (연환산 %)
            systematicShare : float — systematic 비중 (% of total variance)
            factorContributions : dict[str, float] — 팩터별 기여 (% of systematic, SMB/HML/RMW/CMA)
            loadings : dict[str, float] — B 벡터 (팩터별 노출)
            interpretation : str — 정성 평가

    Examples:
        >>> from dartlab.quant.factor.calc import calcMultiFactorRisk
        >>> r = calcMultiFactorRisk("005930")
        >>> print(r["systematicShare"], r["interpretation"])

    Notes:
        - sys_var = B^T Σ_f B  (팩터 공분산 × 노출 quadratic form)
        - 팩터별 기여 = B_k × (Σ_f B)_k / sys_var (marginal contribution to risk)
        - residual 은 decomposeFactor 의 residualRisk (이미 annualized) 사용
    """
    decomp = decomposeFactor(stockCode, market=market)
    if not decomp or "error" in decomp:
        return decomp

    from dartlab.quant.factor.build import buildFactors

    actual_market = decomp.get("market", market)
    fb = buildFactors(actual_market)
    if fb is None:
        return None

    # 팩터 시계열 stack (사용 가능한 팩터만)
    factor_arrays = []
    factor_names = []
    for name in ("smb", "hml", "rmw", "cma"):
        arr = fb.get(name)
        if arr is not None:
            factor_arrays.append(np.asarray(arr, dtype=np.float64))
            factor_names.append(name.upper())
    if not factor_arrays:
        return None

    ml = min(len(a) for a in factor_arrays)
    if ml < 30:
        return None
    F = np.column_stack([a[-ml:] for a in factor_arrays])  # T × K
    Sigma_f = np.cov(F.T, ddof=1) * 252  # K × K (annualized)

    # 종목의 팩터 노출 B (decomposeFactor loadings)
    loadings = []
    for name in factor_names:
        info = decomp.get(name)
        if isinstance(info, dict):
            loadings.append(float(info.get("loading", 0.0)))
        else:
            loadings.append(0.0)
    B = np.array(loadings, dtype=np.float64)

    # systematic variance = B^T Σ_f B (연환산)
    sys_var = float(B @ Sigma_f @ B)
    sys_var = max(sys_var, 0.0)
    sys_risk_pct = float(np.sqrt(sys_var)) * 100  # %

    # residual = decomposeFactor 의 residualRisk (이미 annualized 비율)
    res_risk_raw = float(decomp.get("residualRisk", 0.0))
    res_var = res_risk_raw**2  # variance
    res_risk_pct = res_risk_raw * 100  # %

    total_var = sys_var + res_var
    total_risk_pct = float(np.sqrt(total_var)) * 100  # %
    sysShare = (sys_var / total_var * 100) if total_var > 0 else 0.0

    # 팩터별 marginal contribution = B_k × (Σ_f B)_k / sys_var
    Sigma_f_B = Sigma_f @ B
    factorContrib: dict[str, float] = {}
    for i, name in enumerate(factor_names):
        marginal = float(Sigma_f_B[i]) * float(B[i])
        contrib = (marginal / sys_var * 100) if sys_var > 0 else 0.0
        factorContrib[name] = round(contrib, 1)

    return {
        "stockCode": stockCode,
        "market": actual_market,
        "model": f"Barra-style FF{len(factor_names)} Multi-Factor",
        "systematicRisk": round(sys_risk_pct, 2),
        "residualRisk": round(res_risk_pct, 2),
        "totalRisk": round(total_risk_pct, 2),
        "systematicShare": round(sysShare, 1),
        "factorContributions": factorContrib,
        "loadings": {n: round(float(B[i]), 3) for i, n in enumerate(factor_names)},
        "interpretation": _interpretRiskDecomp(sysShare, factorContrib),
    }


def _interpretRiskDecomp(sysShare: float, factorContrib: dict) -> str:
    """systematic 비중 + 최대 기여 팩터 → 정성 평가."""
    if sysShare > 70:
        kind = "팩터 의존 (시장 분산효과 큼)"
    elif sysShare > 50:
        kind = "팩터 + 고유 균형"
    elif sysShare > 30:
        kind = "고유 리스크 우세"
    else:
        kind = "거의 idiosyncratic (팩터 노출 작음)"
    if not factorContrib:
        return kind
    top = max(factorContrib.items(), key=lambda x: abs(x[1]))
    return f"{kind} | 최대 팩터 기여: {top[0]} ({top[1]:+.1f}%)"


def calcFactorTearSheetAll(*, market: str = "KR") -> dict | None:
    """4 표준 팩터 (SMB/HML/RMW/CMA) 의 tear sheet 종합 — story 시장분석 섹션 자동 사용.

    Capabilities:
        - 4 팩터 동시 평가 (한 번 buildFactors 호출 후 4개 metric)
        - 각 팩터의 Sharpe 비교 → 한국 시장 강한 alpha 원천 즉시 식별
        - story 의 ``factorTearSheetBlock`` 가 직접 호출

    Args:
        market: ``"KR"`` | ``"US"``. 기본 ``"KR"``.

    Returns:
        dict
            market : str
            year : str
            universe : int
            isRealFamaFrench : bool
            factors : list[dict] — 각 dict 는 calcFactorTearSheet 결과
            strongest : str | None — 가장 강한 |Sharpe| 팩터명
            interpretation : str — 종합 정성 평가
    """
    factors = []
    for fname in ("smb", "hml", "rmw", "cma"):
        ts = calcFactorTearSheet(fname, market=market)
        if ts is not None:
            factors.append(ts)
    if not factors:
        return None

    strongest = max(factors, key=lambda x: abs(x.get("longShortSharpe", 0)))
    return {
        "market": market,
        "year": factors[0].get("year"),
        "universe": factors[0].get("universe"),
        "isRealFamaFrench": factors[0].get("isRealFamaFrench"),
        "factors": factors,
        "strongest": strongest.get("factorName"),
        "interpretation": (
            f"{market} 시장 가장 강한 팩터: {strongest.get('factorName')} "
            f"(Sharpe={strongest.get('longShortSharpe')}, "
            f"{strongest.get('interpretation')})"
        ),
    }


_FACTOR_KEY_MAP = {
    "size": ("marketCap", False),
    "value": ("bookToMarket", True),
    "quality": ("roe", True),
    "investment": ("assetGrowth", False),
    "smb": ("marketCap", False),
    "hml": ("bookToMarket", True),
    "rmw": ("roe", True),
    "cma": ("assetGrowth", False),
}


def calcFactorIC(
    factorName: str = "value",
    *,
    market: str = "KR",
    horizon: int = 1,
) -> dict | None:
    """팩터의 Cross-Sectional Information Coefficient 시계열 — Grinold & Kahn Ch.5 표준.

    Capabilities:
        - 일별 횡단면 Spearman IC = corr(factor rank, forward return rank) across stocks
        - IC mean / IC std / ICIR (IC_mean / IC_std × √252) = Fundamental Law breadth 원료
        - Hit rate (IC>0 일 비율) + 누적 IC 신호 안정성 진단
        - horizon 옵션으로 1d/5d/20d forward return IC 비교

    AIContext:
        - story 시장분석 섹션의 ``factorICBlock`` 가 자동 호출 (향후)
        - Alphalens 표준 metric (팩터 tear sheet 의 long-short Sharpe 와 독립 평가)
        - ICIR > 0.5 = 강한 예측력, > 0.3 = 중간, < 0.1 = 노이즈
        - Grinold & Kahn Fundamental Law: IR ≈ IC × √breadth

    Guide:
        - "value 팩터 예측력" → calcFactorIC("value")
        - "size 팩터 5일 forward IC" → calcFactorIC("size", horizon=5)
        - "quality 팩터 월간" → calcFactorIC("quality", horizon=20)

    SeeAlso:
        - calcFactorTearSheet : long-short portfolio Sharpe (Alphalens 보완)
        - decomposeFactor : 단일 종목 FF5 loadings
        - fundamentalLawIR : IC + breadth → IR 공식

    Args:
        factorName: ``"size" | "value" | "quality" | "investment"``
            (별칭 ``"smb" | "hml" | "rmw" | "cma"`` 허용). 기본 ``"value"``.
        market: ``"KR"`` 만 지원 (연말 MKTCAP/펀더멘털 SSOT).
        horizon: forward return 기간 (일). ``1`` / ``5`` / ``20`` 권장. 기본 ``1``.

    Returns:
        dict
            factorName : str — 대문자 팩터명
            horizon : int — forward return 기간 (일)
            market : str — "KR"
            fundYear : str — 펀더멘털 기준 연도 (전년, look-ahead 방지)
            retYear : str — 수익률 관측 연도 (당해, Q2~Q4)
            nStocks : int — IC 계산에 포함된 종목 수
            nDays : int — IC 시계열 관측일 수
            icMean : float — 평균 Spearman IC (배, -1.0~1.0)
            icStd : float — IC 표준편차 (배)
            icir : float — IC Information Ratio (icMean/icStd × √(252/h), 배)
            hitRate : float — IC > 0 구간 비율 (%)
            tStat : float — IC mean t-통계량 (= icMean × √nDays / icStd)
            interpretation : str — 정성 평가 ("강한 예측력" 등)
            notes : str — 데이터 source

    Examples:
        >>> from dartlab.quant.factor.calc import calcFactorIC
        >>> ic = calcFactorIC("value", horizon=5)
        >>> print(ic["icir"], ic["interpretation"])
        0.42 중간 예측력 (value)

    Notes:
        - Spearman (rank 기반) — outlier robust.
        - forward return = log(close[t+h]/close[t]).
        - 전년 연말 펀더멘털 snapshot → 당해년도 Q2~Q4 (look-ahead bias 방지).
        - **non-overlapping h-일 stepping** — 자기상관 제거, ICIR 인플레이션 방지.
        - 한 시점 cross-section 최소 20 종목 미만은 제외.
        - ICIR = icMean / icStd × √(252/h) = 연환산.
    """
    fname = factorName.lower().strip()
    if fname not in _FACTOR_KEY_MAP:
        raise ValueError(
            f"factorName 알 수 없음: {factorName!r} — 허용: size/value/quality/investment (또는 smb/hml/rmw/cma)"
        )
    metric_key, reverse_sign = _FACTOR_KEY_MAP[fname]

    if market != "KR":
        return None

    try:
        from dartlab.core.cross.scanBridge import extractAnnualConsolidated
        from dartlab.gather._hfBulk import loadFiltered
        from dartlab.quant.factor.build import _buildUniverseMetrics, _latestYear
        from dartlab.quant.screen.dataAccess import loadScanParquet
    except Exception as exc:  # noqa: BLE001
        log.warning("calcFactorIC import 실패: %s", type(exc).__name__)
        return None

    try:
        lf = loadScanParquet("finance", market)
        if lf is None:
            return None
        snap = extractAnnualConsolidated(lf.collect())
        year = _latestYear(snap)
        if year is None:
            return None
    except Exception as exc:  # noqa: BLE001
        log.warning("calcFactorIC year 추출 실패: %s", type(exc).__name__)
        return None

    # look-ahead bias 방지: 전년도 펀더멘털 → 당해년도 수익률
    # (전년 12월말 데이터는 당해년도 Q1 이후 공시되므로 실전 예측 가능)
    try:
        fund_year = str(int(str(year)) - 1)
    except ValueError:
        return None
    ret_year = str(year)

    metrics = _buildUniverseMetrics(market, fund_year)
    if len(metrics) < 50:
        return None

    scores = {code: m[metric_key] for code, m in metrics.items() if m.get(metric_key) is not None}
    if len(scores) < 50:
        return None
    if reverse_sign:
        # higher raw = higher factor exposure (good)
        pass

    try:
        long_df = loadFiltered(
            start=f"{ret_year}-04-01",
            end=f"{ret_year}-12-31",
            adjustment="raw",
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("calcFactorIC loadFiltered 실패: %s", type(exc).__name__)
        return None
    if long_df is None or long_df.is_empty():
        return None

    import polars as pl

    codes = list(scores.keys())
    sub = long_df.filter(pl.col("ISU_CD").is_in(codes)).select(["BAS_DD", "ISU_CD", "TDD_CLSPRC"])
    if sub.is_empty():
        return None

    wide = sub.pivot(values="TDD_CLSPRC", index="BAS_DD", on="ISU_CD", aggregate_function="first").sort("BAS_DD")
    date_col = wide.get_column("BAS_DD").to_numpy()
    stock_cols = [c for c in wide.columns if c != "BAS_DD"]
    if len(stock_cols) < 20:
        return None

    px = wide.select(stock_cols).to_numpy().astype(np.float64)
    # forward log returns horizon h — non-overlapping stepping (자기상관 제거)
    h = max(1, int(horizon))
    if px.shape[0] <= h + 1:
        return None
    start_indices = np.arange(0, px.shape[0] - h, h)
    if len(start_indices) < 10:
        return None
    with np.errstate(divide="ignore", invalid="ignore"):
        fwd = np.log(px[start_indices + h] / px[start_indices])

    score_vec = np.array([scores[c] for c in stock_cols], dtype=np.float64)

    ic_series = []
    for t in range(fwd.shape[0]):
        row = fwd[t]
        valid = np.isfinite(row) & np.isfinite(score_vec)
        if valid.sum() < 20:
            continue
        sr = _rank1d(score_vec[valid])
        rr = _rank1d(row[valid])
        if sr.std() == 0 or rr.std() == 0:
            continue
        ic = float(np.corrcoef(sr, rr)[0, 1])
        if np.isfinite(ic):
            ic_series.append(ic)

    if len(ic_series) < 10:
        return None

    # non-overlapping h-일 IC → 연간 관측 수 = 252/h
    periods_per_year = TRADING_DAYS / h
    ic_arr = np.asarray(ic_series, dtype=np.float64)
    ic_mean = float(ic_arr.mean())
    ic_std = float(ic_arr.std(ddof=1))
    icir = (ic_mean / ic_std * np.sqrt(periods_per_year)) if ic_std > 0 else 0.0
    hit_rate = float((ic_arr > 0).mean()) * 100
    t_stat = ic_mean / (ic_std / np.sqrt(len(ic_arr))) if ic_std > 0 else 0.0

    return {
        "factorName": fname.upper(),
        "horizon": h,
        "market": market,
        "fundYear": fund_year,
        "retYear": ret_year,
        "nStocks": len(stock_cols),
        "nDays": int(len(ic_arr)),
        "icMean": round(ic_mean, 4),
        "icStd": round(ic_std, 4),
        "icir": round(icir, 3),
        "hitRate": round(hit_rate, 2),
        "tStat": round(float(t_stat), 2),
        "interpretation": _interpretIC(icir, fname, nDays=len(ic_arr)),
        "notes": (
            f"Spearman cross-sectional IC. fundYear={fund_year} → retYear={ret_year} Q2~Q4, "
            f"horizon={h}d non-overlap stepping, score={metric_key}. "
            "전년 연말 펀더멘털 → 당해 수익률 (look-ahead bias 방지), "
            "non-overlap 으로 자기상관 제거."
        ),
    }


def _rank1d(arr: np.ndarray) -> np.ndarray:
    """1D array → rank (ties averaged, 1-based normalized to 0..1 scale irrelevant)."""
    order = arr.argsort()
    ranks = np.empty_like(order, dtype=np.float64)
    ranks[order] = np.arange(len(arr), dtype=np.float64)
    # tie-averaging
    uniq, inv = np.unique(arr, return_inverse=True)
    if len(uniq) < len(arr):
        sums = np.zeros(len(uniq), dtype=np.float64)
        counts = np.zeros(len(uniq), dtype=np.float64)
        np.add.at(sums, inv, ranks)
        np.add.at(counts, inv, 1.0)
        avg = sums / counts
        ranks = avg[inv]
    return ranks


def _interpretIC(icir: float, factor: str, *, nDays: int | None = None) -> str:
    """ICIR + 팩터 → 정성 한 줄. 단년도 sample 한계 caveat 포함."""
    a = abs(icir)
    if a > 2.0:
        level = "매우 강한 예측력 (sample 제한 주의)"
    elif a > 1.0:
        level = "강한 예측력"
    elif a > 0.5:
        level = "중간 예측력"
    elif a > 0.2:
        level = "약한 예측력"
    else:
        level = "노이즈 수준"
    sign = "+" if icir > 0 else "-"
    suffix = ""
    if nDays is not None and nDays < 30:
        suffix = " [단기 sample]"
    return f"{level} ({sign}{factor}){suffix}"


def calcFactorICAll(*, market: str = "KR", horizon: int = 5) -> dict | None:
    """4 팩터 (size/value/quality/investment) 의 Cross-Sectional IC 종합.

    Args:
        market: ``"KR"`` 만 지원.
        horizon: forward return 기간. 기본 ``5`` (주간 시그널).

    Returns:
        dict
            market : str
            year : str
            horizon : int
            factors : list[dict] — 각 dict 는 calcFactorIC 결과
            strongest : str | None — |ICIR| 최대 팩터
            interpretation : str
    """
    rows = []
    for fname in ("size", "value", "quality", "investment"):
        ic = calcFactorIC(fname, market=market, horizon=horizon)
        if ic is not None:
            rows.append(ic)
    if not rows:
        return None
    strongest = max(rows, key=lambda x: abs(x.get("icir", 0)))
    return {
        "market": market,
        "fundYear": rows[0].get("fundYear"),
        "retYear": rows[0].get("retYear"),
        "horizon": horizon,
        "factors": rows,
        "strongest": strongest.get("factorName"),
        "interpretation": (
            f"{market} 시장 IC 최강 팩터: {strongest.get('factorName')} "
            f"(ICIR={strongest.get('icir')}, {strongest.get('interpretation')})"
        ),
    }


# 0.10 BC 깸 — snake_case alias 제거.

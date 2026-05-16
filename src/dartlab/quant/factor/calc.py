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

from dartlab.core.market import resolveMarket
from dartlab.core.memory import withMemoryBudget
from dartlab.core.polarsUtil import isEmptyDf
from dartlab.quant.screen.dataAccess import fetchOhlcv, ohlcvToArrays
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
    market = resolveMarket(stockCode, market)
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


from dartlab.quant.factor._calcHelpers import (
    _capmFallback,
    _interpret,
    _multiOls,
)

# ══════════════════════════════════════════════════════════════════════
# Phase B0 — Alphalens-style Factor Tear Sheet (story 시장분석 섹션)
# ══════════════════════════════════════════════════════════════════════


@withMemoryBudget(limitMb=300)
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


from dartlab.quant.factor._calcHelpers import _interpretFactorSharpe


@withMemoryBudget(limitMb=300)
def calcMultiFactorRisk(stockCode: str, *, market: str = "auto") -> dict | None:
    """Multi-Factor Risk Decomposition — Barra-style B Σ_f Bᵀ + D 분해.

    Capabilities:
        단일 종목의 총 리스크를 4 팩터 (SMB/HML/RMW/CMA) 공분산 행렬과 노출 (loadings) 의
        quadratic form 으로 systematic 부분과 idiosyncratic (residual) 부분으로 분해. 팩터별
        marginal contribution 까지 산출해 "어느 팩터가 위험 주범" 인지 정량.

    Parameters
    ----------
    stockCode : str
        종목코드 (KR 6 자리 또는 US ticker).
    market : str, default "auto"
        "KR" | "US" | "auto".

    Returns
    -------
    dict | None
        stockCode : str — 입력 echo
        market : str — 해석된 시장
        model : str — "Barra-style FF4 Multi-Factor"
        systematicRisk : float — 팩터 기여 리스크 (연환산 %)
        residualRisk : float — 고유 리스크 (idiosyncratic, 연환산 %)
        totalRisk : float — 합산 (연환산 %)
        systematicShare : float — systematic 비중 (% of total variance)
        factorContributions : dict[str, float] — 팩터별 기여 (% of systematic)
        loadings : dict[str, float] — B 벡터 (팩터별 노출)
        interpretation : str — 정성 평가 ("SMB 의존 강한 소형주" 등)
        decompose 실패 시 error dict 반환.

    Raises
    ------
    없음 (오류는 dict["error"]).

    Example
    -------
    >>> r = calcMultiFactorRisk("005930")
    >>> r["systematicShare"], r["factorContributions"]["SMB"]
    (72.4, 41.8)

    Guide
    -----
    sys_var = B^T Σ_f B (quadratic form). 팩터별 기여 = B_k × (Σ_f B)_k / sys_var 의 marginal
    contribution. systematicShare 가 50% 미만이면 종목 고유 변동 우세 — alpha 분석 우선.
    50% 이상이면 팩터 의존 — factorContributions 최대값을 헤지 대상으로 선택.

    SeeAlso
    -------
    - ``dartlab.quant.factor.calc.decomposeFactor`` : loadings (B) 본체
    - ``dartlab.quant.factor.calc.calcFactorTearSheet`` : 팩터별 Sharpe
    - ``dartlab.quant.factor.residual.calcResidual`` : 잔여 alpha

    Requires
    --------
    - L1 gather: 주가 OHLCV 60 거래일 이상
    - L1.5 frame: factor build 결과 (SMB/HML/RMW/CMA 시계열)

    AIContext
    ---------
    "총 리스크 30% 중 systematic 22% / idiosyncratic 8%, SMB +45%" 같은 정량 답변 진입점.
    systematicShare 단독 인용보다 최대 factor contribution 까지 한 줄로 묶어 인용 권장.
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


from dartlab.quant.factor._calcHelpers import _interpretRiskDecomp


@withMemoryBudget(limitMb=500)
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


# IC 평가 함수 — _factorIC.py 분리 (BC: 본 모듈에서 import 가능)
from dartlab.quant.factor._factorIC import _FACTOR_KEY_MAP, calcFactorIC, calcFactorICAll  # noqa: E402, F401

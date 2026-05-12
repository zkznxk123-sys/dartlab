"""Real Options in Valuation — Damodaran.

*Investment Valuation* Ch.28-30:
- Option to Delay (신사업 진입): underlying NPV vs 기다림의 가치
- Option to Expand (확장): 현재 투자 + 미래 확장 권리
- Option to Abandon (축소): 진행 가치 vs 청산/포기 가치

lifeCycle 기반 자동 선택:
- earlyGrowth / highGrowth + R&D > 5% → delay
- matureGrowth + ROIC > WACC → expand
- decline / turnaround → abandon

이중계산 방지 — dFV primary value 에 곱하지 않음. `out["realOptions"]` 서브 dict 만.
"""

from __future__ import annotations

from statistics import pstdev
from typing import Any


def calcRealOptionsValue(
    company: Any,
    *,
    optionType: str | None = None,
    basePeriod: str | None = None,
    overrides: dict | None = None,
) -> dict[str, Any] | None:
    """lifeCycle 기반 Real Option 가치 계산.

    Returns
    -------
    dict | None
        optionType : "delay" | "expand" | "abandon"
        S : 기초자산 현재 가치 (underlying NPV)
        K : 행사가 (투자비용 or 청산가치)
        T : 만기 (년)
        sigma : 변동성 (연환산)
        rf : 무위험수익률
        optionValue : float — 옵션 가격
        intrinsic : float — max(0, S-K) or max(0, K-S)
        timeValue : float — optionValue - intrinsic
        appliedAs : "uplift" | "floor"
        method : "black_scholes" | "binomial"
        warnings : list[str]
    """
    overrides = overrides or {}

    # lifeCycle phase 추출
    try:
        from dartlab.analysis.financial.lifeCycle import calcLifeCycle
        from dartlab.synth.overrides import applyOverride
    except ImportError:
        return None

    forced_phase = applyOverride(None, "lifeCyclePhase", overrides)
    if forced_phase is None:
        lc = calcLifeCycle(company, basePeriod=basePeriod)
        phase = lc.get("phase") if lc else None
    else:
        phase = forced_phase

    if optionType is None:
        optionType = _selectOptionType(phase)
    if optionType is None:
        return None

    # σ 추출 — 영업이익 변동성
    sigma = _computeSigma(company)
    if sigma is None or sigma <= 0:
        return {
            "optionType": optionType,
            "optionValue": None,
            "warnings": ["변동성(sigma) 계산 불가 — history < 3y"],
            "appliedAs": None,
            "method": None,
        }

    # S, K 추출
    sk = _computeSK(company, optionType)
    if sk is None:
        return None
    S, K, rf, T = sk["S"], sk["K"], sk["rf"], sk["T"]

    # Black-Scholes (기본) / Binomial (american 조기행사 가능 시)
    from dartlab.analysis.valuation.optionValue import binomialOption, blackScholesCall

    if optionType == "abandon":
        # put option (계속 vs 포기)
        bs = blackScholesCall(S, K, T, rf, sigma)
        option_value = bs["put"]
        intrinsic = max(0.0, K - S)
        applied_as = "floor"
    else:
        # delay / expand → call
        if optionType == "delay":
            # 미국식 (언제든 실행 가능)
            binom = binomialOption(S, K, T, rf, sigma, steps=50, kind="call", american=True)
            option_value = binom["value"]
            method = "binomial"
        else:
            bs = blackScholesCall(S, K, T, rf, sigma)
            option_value = bs["call"]
            method = "black_scholes"
        intrinsic = max(0.0, S - K)
        applied_as = "uplift"

    time_value = option_value - intrinsic

    return {
        "optionType": optionType,
        "S": S,
        "K": K,
        "T": T,
        "sigma": sigma,
        "rf": rf,
        "optionValue": round(option_value, 2),
        "intrinsic": round(intrinsic, 2),
        "timeValue": round(time_value, 2),
        "appliedAs": applied_as,
        "method": "binomial" if optionType == "delay" else "black_scholes",
        "phase": phase,
        "warnings": [],
    }


def _selectOptionType(phase: str | None) -> str | None:
    """lifeCycle phase → 기본 option type."""
    if phase in ("earlyGrowth", "highGrowth"):
        return "delay"
    if phase == "matureGrowth":
        return "expand"
    if phase in ("decline", "turnaround"):
        return "abandon"
    return None


def _computeSigma(company: Any) -> float | None:
    """영업이익률 시계열 표준편차 → 연환산 σ.

    Damodaran 관습: σ = stdev(OPM) or stdev(FCF growth).
    여기선 OPM 변동계수 사용.
    """
    try:
        from dartlab.analysis.financial.profitability import calcMarginTrend

        m = calcMarginTrend(company)
        if not m or not m.get("history"):
            return None
        margins = [h.get("operatingMargin") for h in m["history"] if isinstance(h.get("operatingMargin"), (int, float))]
        if len(margins) < 3:
            return None
        sigma = pstdev(margins) / 100.0  # % → decimal
        # sanity: [0.05, 1.5]
        return max(0.05, min(sigma, 1.5))
    except (ImportError, AttributeError, ValueError, TypeError):
        return None


def _computeSK(company: Any, optionType: str) -> dict | None:
    """S (underlying NPV), K (strike), rf, T 추출.

    단순화:
    - S = 기존 calcDcf 의 perShareValue (현재 추정 주당 가치)
    - K (delay/expand) = S × 1.2 (20% premium — 실행비용 근사)
    - K (abandon) = liquidation perShare (자산 청산가치)
    - T = 5년 (option 만기 관습)
    - rf = Damodaran Rf
    """
    try:
        from dartlab.analysis.financial.valuation import calcDcf
        from dartlab.analysis.valuation.dFV import _calcLiquidationDetail
        from dartlab.macro.rates.riskPremiums import loadDamodaranERP
    except ImportError:
        return None

    dcf_result = calcDcf(company)
    if not isinstance(dcf_result, dict):
        return None
    S = dcf_result.get("perShareValue")
    if not S or S <= 0:
        return None

    currency = getattr(company, "currency", None)
    erp = loadDamodaranERP(currency=currency)
    rf = erp["riskFreeRate"] / 100.0

    if optionType == "abandon":
        liq = _calcLiquidationDetail(company, {})
        K = liq.get("perShare") if liq else None
        if K is None or K <= 0:
            K = S * 0.5  # fallback 50% of S
    else:
        # delay/expand — 행사가는 "추가 투자비용" — S × 1.2 근사
        K = S * 1.2

    return {"S": float(S), "K": float(K), "rf": rf, "T": 5.0}

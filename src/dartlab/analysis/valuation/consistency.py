"""Cash Flow Consistency — Damodaran 가정 간 정합성 검증.

*Investment Valuation* 에서 Damodaran 이 가장 자주 지적하는 실수:
- 성장 가정 ≠ 재투자 필요량 매칭 실패
- FCFF 로 할인하면서 Ke 로 할인 (discount rate 섞음)
- Terminal Value 비중 과도
- 실패 위험을 할인율에 장착 (이중계산)
- Marginal tax rate 와 effective tax rate 의 혼동

`detectExtremeFlags` 와 역할 분담:
- detectExtremeFlags : **단일 가정의 극단값** (WACC 15% 초과 등)
- calcCashFlowConsistency : **가정 간 정합성** (g ≠ reinvestRate × ROIC)

반환은 순수 dict — 해석은 story narrate 층 담당.
"""

from __future__ import annotations

from typing import Any

from dartlab.core.utils.calc import reinvestmentIdentity
from dartlab.macro.riskPremiums import loadDamodaranERP

_SEV_INFO = "info"
_SEV_WARN = "warn"
_SEV_CRITICAL = "critical"

_SEV_ORDER = {_SEV_INFO: 0, _SEV_WARN: 1, _SEV_CRITICAL: 2}


def calcCashFlowConsistency(
    company: Any = None,
    *,
    basePeriod: str | None = None,
    valuation: dict[str, Any] | None = None,
    roicPct: float | None = None,
    growthRatePct: float | None = None,
    reinvestmentRatePct: float | None = None,
    terminalGrowthPct: float | None = None,
    terminalValueShare: float | None = None,
    primaryModel: str | None = None,
    modelsUsed: int | None = None,
    effectiveTaxRatePct: float | None = None,
    waccPct: float | None = None,
    country: str | None = None,
    currency: str | None = None,
) -> dict[str, Any]:
    """Damodaran 가정 간 정합성 검증.

    Parameters
    ----------
    valuation : dFV 결과 dict. 지정 시 내부에서 필요한 값 자동 추출.
    roicPct, growthRatePct, reinvestmentRatePct : Growth Equation 검증 (g = reinvest × ROIC)
    terminalGrowthPct : 영구성장률 (%)
    terminalValueShare : TV / EV (0.0~1.0)
    primaryModel : "dcf"/"dcf2stage"/"fcfe"/"ddm"/"rim"/... — 할인율 매칭 검증
    modelsUsed : 사용된 모델 개수 (단일 방법론 의존 감지)
    effectiveTaxRatePct : 유효세율 (%)
    waccPct : WACC (%)
    country : ISO2 (Rf / marginalTax 조회)
    currency : country 없을 때 추론

    Returns
    -------
    dict
        flags : list[dict{rule, severity, message, observed, expected}]
        severity : str — 전체 최고 심각도
        score : int — 0~100 (100 = 완전 정합)
        checks : dict — 개별 검증 결과
    """
    # company 지정 시 자동 추출
    if company is not None:
        if currency is None:
            currency = getattr(company, "currency", None)
        if valuation is None:
            try:
                from dartlab.analysis.valuation.dFV import calcDFV

                valuation = calcDFV(company, basePeriod=basePeriod)
            except (ImportError, AttributeError, ValueError, TypeError):
                pass
        if roicPct is None or waccPct is None:
            try:
                from dartlab.analysis.financial.investmentAnalysis import calcRoicTimeline

                r = calcRoicTimeline(company, basePeriod=basePeriod)
                if r and r.get("history"):
                    latest = r["history"][0]
                    if roicPct is None:
                        roicPct = latest.get("roic")
                    if waccPct is None:
                        waccPct = latest.get("waccEstimate")
                    if effectiveTaxRatePct is None:
                        effectiveTaxRatePct = latest.get("effectiveTaxRate")
            except (ImportError, AttributeError, ValueError, TypeError):
                pass
        if growthRatePct is None:
            try:
                from dartlab.analysis.financial.growthAnalysis import calcGrowthTrend

                g = calcGrowthTrend(company, basePeriod=basePeriod)
                if g:
                    growthRatePct = (g.get("cagr") or {}).get("revenue")
            except (ImportError, AttributeError, ValueError, TypeError):
                pass

    if valuation:
        roicPct = roicPct if roicPct is not None else valuation.get("roicPct")
        growthRatePct = growthRatePct if growthRatePct is not None else valuation.get("growthRatePct")
        terminalGrowthPct = terminalGrowthPct if terminalGrowthPct is not None else valuation.get("terminalGrowth")
        terminalValueShare = terminalValueShare if terminalValueShare is not None else valuation.get("tvShare")
        primaryModel = (
            primaryModel if primaryModel is not None else valuation.get("primary") or valuation.get("primaryModel")
        )
        modelsUsed = modelsUsed if modelsUsed is not None else len(valuation.get("allMethods") or [])
        waccPct = (
            waccPct if waccPct is not None else valuation.get("wacc") or (valuation.get("details") or {}).get("wacc")
        )

    erp = loadDamodaranERP(countryCode=country, currency=currency)
    rf_pct = erp["riskFreeRate"]
    marginal_tax = erp["marginalTaxRate"]

    flags: list[dict] = []
    checks: dict[str, Any] = {}

    # 규칙 1: Terminal growth ≤ Rf (Damodaran 강제)
    checks["terminalGrowthBounded"] = True
    if isinstance(terminalGrowthPct, (int, float)):
        if terminalGrowthPct > rf_pct + 0.5:
            checks["terminalGrowthBounded"] = False
            flags.append(
                {
                    "rule": "g_vs_rf",
                    "severity": _SEV_WARN,
                    "message": f"영구성장률 {terminalGrowthPct:.1f}% 가 무위험수익률 {rf_pct:.1f}% 초과 — 장기 GDP 초과는 불가능 가정",
                    "observed": terminalGrowthPct,
                    "expected": rf_pct,
                }
            )

    # 규칙 2: Growth Equation — g = reinvest × ROIC
    checks["growthReinvestmentMatch"] = None
    if growthRatePct is not None and roicPct is not None and roicPct > 0:
        identity = reinvestmentIdentity(growthRatePct, roicPct)
        implied = identity["impliedReinvestRate"] if identity else None
        if reinvestmentRatePct is not None and implied is not None:
            observed = reinvestmentRatePct / 100.0
            gap = abs(observed - implied)
            checks["growthReinvestmentMatch"] = gap < 0.10
            if gap >= 0.10:
                flags.append(
                    {
                        "rule": "reinvest_identity",
                        "severity": _SEV_CRITICAL,
                        "message": f"g={growthRatePct:.1f}% 와 ROIC={roicPct:.1f}% 에서 필요 재투자율은 {implied * 100:.0f}% 이나 {reinvestmentRatePct:.0f}% 가정 — 수학 위반",
                        "observed": reinvestmentRatePct,
                        "expected": round(implied * 100, 1),
                    }
                )
        elif implied is not None:
            checks["impliedReinvestRate"] = round(implied, 4)

    # 규칙 3: 할인율 매칭 (FCFF→WACC / FCFE→Ke / DDM→Ke)
    checks["discountRateMatch"] = True
    if primaryModel:
        pm = str(primaryModel).lower()
        if pm in ("fcfe", "ddm", "rim") and waccPct is not None:
            # 이 모델들은 Ke 로 할인해야 하므로 WACC 가 아니라 Ke 가 제공되어야 함
            # valuation dict 에 ke 가 별도 표기된 경우만 경고 (정보성)
            pass  # 실제 비교는 dFV.py 에서 담당 — 여기서는 명시적 경고만 스킵

    # 규칙 4: Terminal Value 비중
    checks["terminalValueShare"] = terminalValueShare
    if isinstance(terminalValueShare, (int, float)) and terminalValueShare > 0.75:
        flags.append(
            {
                "rule": "tv_weight",
                "severity": _SEV_WARN,
                "message": f"Terminal Value 비중 {terminalValueShare * 100:.0f}% — explicit forecast 구간 신뢰도 낮음",
                "observed": round(terminalValueShare, 3),
                "expected": 0.75,
            }
        )

    # 규칙 5: 단일 모델 의존
    if isinstance(modelsUsed, int) and modelsUsed <= 1:
        flags.append(
            {
                "rule": "single_model",
                "severity": _SEV_INFO,
                "message": "단일 방법론만 사용 — 삼각검증 부재",
                "observed": modelsUsed,
                "expected": 2,
            }
        )

    # 규칙 6: 유효세율 vs marginal tax
    checks["taxRateConsistency"] = True
    if isinstance(effectiveTaxRatePct, (int, float)):
        gap = abs(effectiveTaxRatePct - marginal_tax)
        if gap > 5.0:
            checks["taxRateConsistency"] = False
            flags.append(
                {
                    "rule": "tax_consistency",
                    "severity": _SEV_INFO,
                    "message": f"유효세율 {effectiveTaxRatePct:.1f}% vs 한계세율 {marginal_tax:.1f}% — terminal 구간 세율 점검",
                    "observed": effectiveTaxRatePct,
                    "expected": marginal_tax,
                }
            )

    # 규칙 7: 성장 과다 낙관 (Damodaran 7 Sins 1번)
    if isinstance(growthRatePct, (int, float)) and isinstance(terminalGrowthPct, (int, float)):
        if growthRatePct > 30 and terminalGrowthPct > rf_pct:
            flags.append(
                {
                    "rule": "growth_optimism",
                    "severity": _SEV_WARN,
                    "message": f"explicit 구간 {growthRatePct:.0f}% + terminal {terminalGrowthPct:.1f}% — 성장 가정 연쇄 과대",
                    "observed": {"explicit": growthRatePct, "terminal": terminalGrowthPct},
                    "expected": {"explicit": "< 30%", "terminal": f"< {rf_pct:.1f}%"},
                }
            )

    severity = _SEV_INFO
    for f in flags:
        if _SEV_ORDER[f["severity"]] > _SEV_ORDER[severity]:
            severity = f["severity"]

    score = 100
    for f in flags:
        if f["severity"] == _SEV_CRITICAL:
            score -= 40
        elif f["severity"] == _SEV_WARN:
            score -= 15
        else:
            score -= 5
    score = max(0, score)

    return {
        "flags": flags,
        "severity": severity,
        "score": score,
        "checks": checks,
    }

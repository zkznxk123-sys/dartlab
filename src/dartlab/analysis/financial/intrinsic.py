"""내재가치 평가 — Owner Earnings · DCF (3 시나리오) · Moat proxy · Snowflake 5 점.

가치투자·종합 평점 view 의 dashboard 카드용 *간이* 정의. 학문적 정확도는
DCF 모델·해자 분석 후속 PR. 본 모듈은 dashboard 노출 + 1 차 신호 한정.

설계:
- 모든 함수 입력은 `company` 객체 (rawFinance + _finance.ratios 노출).
- 결측·예외는 None 반환 (renderer 가 placeholder).
- 상수 (WACC 8% / 영구성장률 2.5% / 5y projection) 은 module 상단 SSOT.
"""

from __future__ import annotations

from typing import Any

_WACC_DEFAULT = 0.08
_TERMINAL_GROWTH = 0.025
_PROJECTION_YEARS = 5


def _ratio(company: Any, name: str) -> float | None:
    try:
        return getattr(company._finance.ratios, name, None)
    except (AttributeError, ValueError):
        return None


def _safe(v: Any) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return f


def calcOwnerEarnings(company: Any) -> dict[str, Any]:
    """Buffett Owner Earnings = 순이익 + 감가상각 − 유지 CapEx.

    유지 CapEx 데이터 부재 → 총 CapEx 의 70% 로 근사. 후속 PR 에서 산업별
    capex/매출 비율 보정.
    """
    ni = _safe(_ratio(company, "netIncomeTTM"))
    da = _safe(_ratio(company, "depreciationTTM"))
    capex = _safe(_ratio(company, "capexTTM"))
    if ni is None:
        return {"value": None, "components": {}}
    maintCapex = capex * 0.7 if capex is not None else 0.0
    daSafe = da or 0.0
    owner = ni + daSafe - maintCapex
    return {
        "value": owner,
        "components": {
            "netIncome": ni,
            "depreciation": daSafe,
            "maintenanceCapex": maintCapex,
        },
    }


def _projectFcf(fcf0: float, growth: float, years: int) -> list[float]:
    out = []
    cur = fcf0
    for _ in range(years):
        cur = cur * (1.0 + growth)
        out.append(cur)
    return out


def _discount(cashflows: list[float], rate: float) -> float:
    pv = 0.0
    for i, cf in enumerate(cashflows, start=1):
        pv += cf / ((1.0 + rate) ** i)
    return pv


def calcDcfIntrinsic(
    company: Any,
    *,
    wacc: float = _WACC_DEFAULT,
    terminalGrowth: float = _TERMINAL_GROWTH,
    years: int = _PROJECTION_YEARS,
) -> dict[str, Any]:
    """DCF 3 시나리오 — Bear/Base/Bull 성장률로 5y projection + terminal.

    성장률은 회사 매출 5y CAGR 을 base 로 ±5%p. CAGR 부재 시 base=5%.
    반환 dict: {bear/base/bull: {growth, pvFcf, pvTerminal, intrinsic}}.
    """
    fcf = _safe(_ratio(company, "fcf")) or _safe(_ratio(company, "fcfTTM"))
    cagr = _safe(_ratio(company, "revenueCagr5y"))
    if fcf is None or fcf <= 0:
        return {"scenarios": {}, "baseFcf": fcf}
    base = cagr if cagr is not None else 0.05
    scenarios: dict[str, dict[str, Any]] = {}
    for tag, g in (("bear", base - 0.05), ("base", base), ("bull", base + 0.05)):
        proj = _projectFcf(fcf, g, years)
        pvFcf = _discount(proj, wacc)
        terminalFcf = proj[-1] * (1.0 + terminalGrowth)
        terminal = terminalFcf / max(wacc - terminalGrowth, 0.005)
        pvTerminal = terminal / ((1.0 + wacc) ** years)
        scenarios[tag] = {
            "growth": round(g * 100, 2),
            "pvFcf": pvFcf,
            "pvTerminal": pvTerminal,
            "intrinsic": pvFcf + pvTerminal,
        }
    return {"scenarios": scenarios, "baseFcf": fcf, "wacc": wacc, "terminalGrowth": terminalGrowth}


def calcMoatProxy(company: Any, *, wacc: float = _WACC_DEFAULT) -> dict[str, Any]:
    """경제적 해자 proxy — ROIC vs WACC 5y avg. ROIC > WACC 지속 = 해자.

    `_finance.ratios.roic` (또는 5y avg) 비교. WACC 기본 8%. 갭이 ≥ 5%p 면
    강한 해자, 0~5%p 약한 해자, < 0 무해자.
    """
    roic = _safe(_ratio(company, "roic5yAvg")) or _safe(_ratio(company, "roic"))
    if roic is None:
        return {"roic": None, "wacc": wacc, "spread": None, "label": "unknown"}
    spread = (roic / 100.0) - wacc if roic > 1 else roic - wacc
    if spread >= 0.05:
        label = "강한 해자"
    elif spread >= 0:
        label = "약한 해자"
    else:
        label = "무해자"
    return {
        "roic": roic,
        "wacc": wacc,
        "spread": round(spread * 100, 2),
        "label": label,
    }


def _normalize(value: float | None, *, low: float, high: float) -> float:
    """value 를 [low, high] 범위에서 0~5 스코어로 정규화."""
    if value is None:
        return 0.0
    if high <= low:
        return 0.0
    v = max(low, min(high, value))
    return round((v - low) / (high - low) * 5.0, 2)


def calcSnowflake5Score(company: Any) -> dict[str, float]:
    """Simply Wall St 5 차원 — Value/Future/Past/Health/Dividend 각 0~5.

    각 차원은 1 개 대표 지표 정규화 (간이). 후속 PR 에서 다지표 합성.
    - Value: PER (낮을수록 좋음, 5~30 range)
    - Future: 매출 CAGR (-10~30 range)
    - Past: ROE (0~30 range)
    - Health: 이자보상배율 (0~20 range)
    - Dividend: 배당수익률 (0~6 range)
    """
    per = _safe(_ratio(company, "per"))
    cagr = _safe(_ratio(company, "revenueCagr5y"))
    roe = _safe(_ratio(company, "roe"))
    ic = _safe(_ratio(company, "interestCoverage"))
    dy = _safe(_ratio(company, "dividendYield"))
    # Value 는 PER 낮을수록 좋음 → 역정규화.
    if per is not None and 5 <= per <= 30:
        value = round((30 - per) / 25 * 5.0, 2)
    elif per is not None and per < 5:
        value = 5.0
    elif per is not None and per > 30:
        value = 1.0
    else:
        value = 0.0
    return {
        "value": value,
        "future": _normalize(cagr * 100 if cagr is not None and abs(cagr) < 1.5 else cagr, low=-10, high=30),
        "past": _normalize(roe, low=0, high=30),
        "health": _normalize(ic, low=0, high=20),
        "dividend": _normalize(dy * 100 if dy is not None and dy < 1 else dy, low=0, high=6),
    }


__all__ = [
    "calcDcfIntrinsic",
    "calcMoatProxy",
    "calcOwnerEarnings",
    "calcSnowflake5Score",
]

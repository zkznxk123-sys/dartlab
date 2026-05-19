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


def _avgScore(vals: list[float | None]) -> float:
    """None 제외 평균. 비면 0.0."""
    nums = [v for v in vals if isinstance(v, (int, float)) and v is not None]
    if not nums:
        return 0.0
    return round(sum(nums) / len(nums), 2)


def _scoreOwnerEarningsYield(company: Any) -> float | None:
    """Owner Earnings Yield (회계 EV 대체) — Owner / (assets - cash) 1~15% 가 0~5."""
    oe = calcOwnerEarnings(company).get("value")
    assets = _safe(_ratio(company, "totalAssetsLatest")) or _safe(_ratio(company, "assets"))
    cash = _safe(_ratio(company, "cashLatest")) or _safe(_ratio(company, "cash"))
    if oe is None or assets is None:
        return None
    ev = assets - (cash or 0)
    if ev <= 0:
        return None
    yld = oe / ev * 100
    return _normalize(yld, low=1, high=15)


def _scoreFcfYieldAccountingEV(company: Any) -> float | None:
    """FCF Yield (회계 EV) — FCF / (자기자본+부채-현금) 1~15% → 0~5."""
    fcf = _safe(_ratio(company, "fcf")) or _safe(_ratio(company, "fcfTTM"))
    equity = _safe(_ratio(company, "equity")) or _safe(_ratio(company, "equityLatest"))
    debt = _safe(_ratio(company, "totalDebt")) or _safe(_ratio(company, "totalDebtLatest"))
    cash = _safe(_ratio(company, "cash")) or _safe(_ratio(company, "cashLatest"))
    if fcf is None or equity is None:
        return None
    ev = equity + (debt or 0) - (cash or 0)
    if ev <= 0:
        return None
    return _normalize(fcf / ev * 100, low=1, high=15)


def _scoreRevenueCagr3y(company: Any) -> float | None:
    cagr = _safe(_ratio(company, "revenueCagr3y")) or _safe(_ratio(company, "revenueCagr5y"))
    if cagr is None:
        return None
    return _normalize(cagr * 100 if abs(cagr) < 1.5 else cagr, low=-10, high=30)


def _scoreCapexAcceleration(company: Any) -> float | None:
    """CapEx YoY 가속 — Lynch Fisher 신호."""
    val = _safe(_ratio(company, "capexYoyAccel")) or _safe(_ratio(company, "capexYoy"))
    if val is None:
        return None
    return _normalize(val * 100 if abs(val) < 1.5 else val, low=-20, high=50)


def _scoreRndAcceleration(company: Any) -> float | None:
    val = _safe(_ratio(company, "rndYoy")) or _safe(_ratio(company, "rndYoyAccel"))
    if val is None:
        return None
    return _normalize(val * 100 if abs(val) < 1.5 else val, low=-10, high=40)


def _scoreRoeRoaRoic(company: Any) -> float:
    """과거 수익성 — ROE + ROA + ROIC 평균 (5y avg 우선)."""
    roe = _safe(_ratio(company, "roe5yAvg")) or _safe(_ratio(company, "roe"))
    roa = _safe(_ratio(company, "roa5yAvg")) or _safe(_ratio(company, "roa"))
    roic = _safe(_ratio(company, "roic5yAvg")) or _safe(_ratio(company, "roic"))
    scores = [_normalize(v, low=0, high=30) if v is not None else None for v in (roe, roa, roic)]
    return _avgScore(scores)


def _scorePiotroskiScaled(company: Any) -> float:
    """Piotroski F-Score 0~9 → 0~5."""
    try:
        from dartlab.analysis.financial import research as _research

        if hasattr(_research, "calcPiotroskiDetail"):
            result = _research.calcPiotroskiDetail(company)
            score = result.get("score") if isinstance(result, dict) else None
            if score is not None:
                return _normalize(score, low=0, high=9)
    except (ImportError, AttributeError, ValueError, TypeError):
        pass
    # Fallback: 이자보상배율 기반 간이.
    ic = _safe(_ratio(company, "interestCoverage"))
    return _normalize(ic, low=0, high=20) if ic is not None else 0.0


def _scorePayoutRatio(company: Any) -> float | None:
    dp = _safe(_ratio(company, "dividendsPaid")) or _safe(_ratio(company, "dividendsPaidTTM"))
    ni = _safe(_ratio(company, "netIncomeTTM")) or _safe(_ratio(company, "netIncome"))
    if dp is None or ni is None or ni <= 0:
        return None
    payout = abs(dp) / ni * 100
    return _normalize(payout, low=10, high=60)


def _scoreRetainedCumulative(company: Any) -> float | None:
    """RE 누적 증가율 — 내부 유보 강건성."""
    growth = _safe(_ratio(company, "retainedEarningsCagr5y"))
    if growth is None:
        return None
    return _normalize(growth * 100 if abs(growth) < 1.5 else growth, low=0, high=20)


def calcSnowflake5Score(company: Any) -> dict[str, float]:
    """Simply Wall St 5 차원 — 회계 대체 metric 으로 정규화 (v3-r5 §C).

    시장가 의존 (PER/PBR/배당수익률) 제거 → 회계 정보만으로 5 차원 측정.
    각 차원은 *다지표 합성 평균* (None 제외).

    - **Value**: Owner Earnings Yield (EV 회계 대체) + FCF Yield (EV 회계 대체)
    - **Future**: 매출 CAGR3y + CapEx YoY 가속 + R&D YoY 가속
    - **Past**: ROE + ROA + ROIC (5y avg 우선)
    - **Health**: Piotroski F-Score scaled (없으면 이자보상배율 fallback)
    - **Dividend**: 배당성향 + 이익잉여금 5y CAGR
    """
    value = _avgScore([_scoreOwnerEarningsYield(company), _scoreFcfYieldAccountingEV(company)])
    future = _avgScore([_scoreRevenueCagr3y(company), _scoreCapexAcceleration(company), _scoreRndAcceleration(company)])
    past = _scoreRoeRoaRoic(company)
    health = _scorePiotroskiScaled(company)
    dividend = _avgScore([_scorePayoutRatio(company), _scoreRetainedCumulative(company)])
    return {
        "value": value,
        "future": future,
        "past": past,
        "health": health,
        "dividend": dividend,
    }


__all__ = [
    "calcDcfIntrinsic",
    "calcMoatProxy",
    "calcOwnerEarnings",
    "calcSnowflake5Score",
]

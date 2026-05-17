"""주가 내재 매출 역산 엔진 — 시장이 합의한 미래 매출을 현재 시가총액에서 역산."""

from __future__ import annotations

from dataclasses import dataclass, field

from dartlab.core.utils.extract import getTTM


@dataclass
class PriceImpliedRevenue:
    """주가 내재 매출 역산 결과."""

    impliedGrowthRate: float  # 시장이 내재하는 매출 성장률 (%, 연간)
    impliedRevenue: list[float]  # 내재 향후 N년 매출
    currentPrice: float
    marketCap: float  # 시가총액 (원)
    latestRevenue: float  # 최근 TTM 매출
    assumedMargin: float  # 가정한 영업이익률 (%)
    assumedWacc: float  # 가정한 WACC (%)
    assumedTerminalGrowth: float  # 가정한 영구성장률 (%)
    gapVsForecast: float | None = None  # 엔진예측 - 시장내재 (%, 양수=시장이 보수적)
    signal: str | None = None  # "underpriced" | "overpriced" | "fair"
    warnings: list[str] = field(default_factory=list)


def reverseImpliedGrowth(
    series: dict,
    marketCap: float,
    *,
    wacc: float = 10.0,
    terminalGrowth: float = 2.0,
    horizon: int = 3,
    netDebt: float | None = None,
) -> PriceImpliedRevenue | None:
    """시가총액에서 시장이 내재하는 매출 성장률을 역산.

    원리: marketCap = PV(미래 FCF) + PV(TV)
    FCF = Revenue × margin × (1 - taxRate) + DA - CAPEX - ΔNWC ≈ Revenue × fcfMargin
    이를 g에 대해 역산하면 시장이 가정하는 매출 성장률이 나온다.

    Capabilities:
        - 이진 탐색으로 EV = DCF(g) 만족하는 g 역산
        - FCF margin 자동 추정 (실제 OCF-CAPEX → revenue 비율, fallback 65%)
        - ±30% hard cap (P/S 고배율 비현실 역산 방지)

    Parameters
    ----------
    series : dict
        finance.timeseries 시계열 dict.
    marketCap : float
        시가총액 (원).
    wacc : float
        가정 할인율 (%, 기본 10).
    terminalGrowth : float
        가정 영구성장률 (%, 기본 2).
    horizon : int
        예측 구간 (년, 기본 3).
    netDebt : float, optional
        순차입금 (EV 보정).

    Returns
    -------
    PriceImpliedRevenue | None
        impliedGrowthRate, impliedRevenue, assumedMargin, assumedWacc,
        assumedTerminalGrowth, warnings. marketCap ≤ 0 또는 revenue 부재 시 None.

    Example:
        >>> r = reverseImpliedGrowth(series, marketCap=4.5e14)
        >>> r.impliedGrowthRate

    Guide:
        wacc ≤ terminalGrowth 시 None. 수렴 실패 시 warning + impliedGrowthRate=0.

    When:
        "시장이 어떤 성장을 가정하고 있나" 질문 + 엔진 예측 대비 갭 분석.

    How:
        reverseImpliedGrowth(series, marketCap=mc) + computeGap(result, forecastG).

    Requires:
        getTTM (revenue/operating_profit/OCF/CAPEX).

    Raises:
        없음.

    See Also:
        - computeGap : 엔진 예측과 시장 내재 갭 + 신호
        - dcfValuation : 정방향 DCF

    AIContext:
        시장 평가 합리성 분석 시 impliedGrowthRate 인용 + 자체 매출 예측과 갭.
    """
    if marketCap is None or marketCap <= 0:
        return None

    revenue = getTTM(series, "IS", "sales") or getTTM(series, "IS", "revenue")
    if revenue is None or revenue <= 0:
        return None

    # 영업이익률 (최근 TTM)
    opIncome = getTTM(series, "IS", "operating_profit") or getTTM(series, "IS", "operating_income")
    margin = opIncome / revenue if opIncome and revenue else 0.0
    if margin <= 0:
        margin = 0.05  # 최소 5% 가정

    # FCF margin 추정: 영업이익률 × (1 - effective tax) - capex/revenue + da/revenue
    # 단순화: FCF margin ≈ 영업이익률 × 0.65 (세금·운전자본·capex 반영)
    fcfMargin = _estimateFcfMargin(series, margin)

    # equity value = marketCap (순부채 조정 생략 or 반영)
    ev = marketCap
    if netDebt is not None:
        ev = marketCap + netDebt

    # 이진 탐색으로 implied growth 역산
    impliedG = _bisectImpliedGrowth(
        ev=ev,
        baseRevenue=revenue,
        fcfMargin=fcfMargin,
        wacc=wacc / 100,
        terminalGrowth=terminalGrowth / 100,
        horizon=horizon,
    )

    warnings: list[str] = []
    if impliedG is None:
        warnings.append("역산 수렴 실패 — 시가총액이 FCF 기반 합리 범위 밖")
        return PriceImpliedRevenue(
            impliedGrowthRate=0.0,
            impliedRevenue=[],
            currentPrice=0.0,
            marketCap=marketCap,
            latestRevenue=revenue,
            assumedMargin=margin * 100,
            assumedWacc=wacc,
            assumedTerminalGrowth=terminalGrowth,
            warnings=warnings,
        )

    # ±30% hard cap (P/S 고배율 기업에서 비현실적 역산 방지)
    _CAP = 0.30
    if abs(impliedG) > _CAP:
        warnings.append(f"내재성장률 {impliedG * 100:+.1f}%가 ±50% 범위 초과 — cap 적용")
        impliedG = max(-_CAP, min(impliedG, _CAP))

    # implied revenue path
    impliedRevPath = []
    rev = revenue
    for _ in range(horizon):
        rev = rev * (1 + impliedG)
        impliedRevPath.append(rev)

    return PriceImpliedRevenue(
        impliedGrowthRate=impliedG * 100,
        impliedRevenue=impliedRevPath,
        currentPrice=0.0,  # 호출자가 설정
        marketCap=marketCap,
        latestRevenue=revenue,
        assumedMargin=margin * 100,
        assumedWacc=wacc,
        assumedTerminalGrowth=terminalGrowth,
        warnings=warnings,
    )


def computeGap(
    implied: PriceImpliedRevenue,
    forecastGrowthRate: float,
) -> None:
    """엔진 예측 성장률 vs 시장 내재 성장률 갭 계산 + 신호 부여.

    Capabilities:
        - gap = forecastGrowthRate - impliedGrowthRate 계산
        - ±5%p 임계 기준 underpriced/overpriced/fair 신호 부여
        - implied 객체에 gapVsForecast/signal 속성 mutate

    Parameters
    ----------
    implied : PriceImpliedRevenue
        reverseImpliedGrowth 결과 (in-place 수정).
    forecastGrowthRate : float
        엔진/AI 예측 매출 성장률 (%).

    Returns
    -------
    None
        in-place 수정 — implied.gapVsForecast/signal 세팅.

    Example:
        >>> computeGap(implied, forecastGrowthRate=8.0)
        >>> implied.signal
        'underpriced'

    Guide:
        gap > 5%p → underpriced, < -5%p → overpriced, 그 외 fair.

    When:
        reverseImpliedGrowth 직후 자체 매출 예측과 비교 단계.

    How:
        computeGap(implied, forecastGrowthRate=engineForecast).

    Requires:
        reverseImpliedGrowth 가 반환한 PriceImpliedRevenue 인스턴스.

    Raises:
        없음.

    See Also:
        - reverseImpliedGrowth : 시장 내재 성장률 역산
        - revenueForecast : 엔진 예측 본체

    AIContext:
        "시장이 보수적/낙관적" 판정 답변 시 gap + signal 인용.
    """
    gap = forecastGrowthRate - implied.impliedGrowthRate
    implied.gapVsForecast = round(gap, 2)

    # 갭 5%p 이상이면 신호
    if gap > 5.0:
        implied.signal = "underpriced"
    elif gap < -5.0:
        implied.signal = "overpriced"
    else:
        implied.signal = "fair"


# ── 내부 유틸 ──────────────────────────────────────────────


def _estimateFcfMargin(series: dict, opMargin: float) -> float:
    """FCF margin 추정 (실제 데이터 기반, fallback 단순화)."""
    revenue = getTTM(series, "IS", "sales") or getTTM(series, "IS", "revenue")
    ocf = getTTM(series, "CF", "operating_cashflow")
    capex = getTTM(series, "CF", "capital_expenditure") or getTTM(
        series, "CF", "purchase_of_property_plant_and_equipment"
    )

    if revenue and revenue > 0 and ocf is not None:
        capexVal = abs(capex) if capex else 0
        fcf = ocf - capexVal
        fcfMargin = fcf / revenue
        # 음수면 영업이익률 기반 fallback (음수 FCF는 일시적일 수 있음)
        if fcfMargin < 0:
            return max(opMargin * 0.50, 0.02)
        # 범위 제한 (0% ~ 40%)
        return max(0.02, min(fcfMargin, 0.40))

    # fallback: 영업이익률 × 65%
    return max(opMargin * 0.65, 0.02)


def _bisectImpliedGrowth(
    ev: float,
    baseRevenue: float,
    fcfMargin: float,
    wacc: float,
    terminalGrowth: float,
    horizon: int,
    *,
    lo: float = -0.50,
    hi: float = 0.60,
    tol: float = 1e-6,
    maxIter: int = 100,
) -> float | None:
    """이진 탐색으로 EV = DCF(g)를 만족하는 g 역산."""
    if wacc <= terminalGrowth:
        return None

    for _ in range(maxIter):
        mid = (lo + hi) / 2
        evCalc = _dcfFromGrowth(baseRevenue, fcfMargin, mid, wacc, terminalGrowth, horizon)

        if abs(evCalc - ev) / max(ev, 1) < tol:
            return mid

        if evCalc < ev:
            lo = mid
        else:
            hi = mid

    # 수렴 못하면 가장 가까운 값 반환
    mid = (lo + hi) / 2
    evCalc = _dcfFromGrowth(baseRevenue, fcfMargin, mid, wacc, terminalGrowth, horizon)
    if abs(evCalc - ev) / max(ev, 1) < 0.05:  # 5% 이내면 허용
        return mid
    return None


def _dcfFromGrowth(
    baseRevenue: float,
    fcfMargin: float,
    growth: float,
    wacc: float,
    terminalGrowth: float,
    horizon: int,
) -> float:
    """주어진 성장률로 DCF 기업가치 계산."""
    rev = baseRevenue
    pvFcf = 0.0
    for yr in range(1, horizon + 1):
        rev = rev * (1 + growth)
        fcf = rev * fcfMargin
        pvFcf += fcf / (1 + wacc) ** yr

    # terminal value (Gordon Growth: TV = FCF_n × (1+g_terminal) / (WACC - g_terminal))
    terminalFcf = rev * fcfMargin
    tv = terminalFcf * (1 + terminalGrowth) / (wacc - terminalGrowth)
    pvTv = tv / (1 + wacc) ** horizon

    return pvFcf + pvTv

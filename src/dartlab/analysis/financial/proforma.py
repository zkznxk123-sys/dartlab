"""3-Statement Pro-Forma 재무제표 엔진.

과거 재무제표에서 구조적 비율을 추출하고,
매출 성장 경로에 따라 IS → BS → CF 연결 모델을 생성한다.

외부 의존성 제로 (math 모듈만 사용).
"""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from dartlab.core.utils.extract import (
    getLatest,
    getTTM,
)

if TYPE_CHECKING:
    from dartlab.core.finance.scenario import SectorElasticity

# ══════════════════════════════════════
# 데이터 구조
# ══════════════════════════════════════


@dataclass
class HistoricalRatios:
    """과거 재무제표에서 추출한 구조적 비율 — pro-forma의 입력."""

    gross_margin: float  # 매출총이익률 (%)
    sga_ratio: float  # 판관비/매출 (%)
    effective_tax_rate: float  # 유효세율 (%)
    depreciation_ratio: float  # 감가상각/매출 (%)
    interest_rate_on_debt: float  # 이자비용/평균차입금 (%)
    nwc_to_revenue: float  # 순운전자본/매출 (%)
    capex_to_revenue: float  # CAPEX/매출 (%) — 양수 저장
    dividend_payout: float  # 배당성향 (%)
    receivables_to_revenue: float  # 매출채권/매출 (%)
    inventory_to_revenue: float  # 재고/매출 (%)
    payables_to_revenue: float  # 매입채무/매출 (%)
    years_used: int
    confidence: str  # "high" | "medium" | "low"
    dep_in_sga: bool = False  # v3: D&A가 SGA에 포함된 IS 구조 (이중 차감 방지)
    warnings: list[str] = field(default_factory=list)
    trends: dict[str, float] = field(default_factory=dict)  # 비율별 연간 트렌드 (v2)

    def __repr__(self) -> str:
        lines = [f"[과거 비율 분석 ({self.years_used}년, 신뢰도: {self.confidence})]"]
        lines.append(f"  매출총이익률: {self.gross_margin:.1f}%")
        lines.append(f"  판관비율: {self.sga_ratio:.1f}%{'  (D&A 포함)' if self.dep_in_sga else ''}")
        lines.append(f"  유효세율: {self.effective_tax_rate:.1f}%")
        lines.append(f"  감가상각/매출: {self.depreciation_ratio:.1f}%{'  (EBITDA 전용)' if self.dep_in_sga else ''}")
        lines.append(f"  CAPEX/매출: {self.capex_to_revenue:.1f}%")
        lines.append(f"  차입 이자율: {self.interest_rate_on_debt:.1f}%")
        lines.append(f"  NWC/매출: {self.nwc_to_revenue:.1f}%")
        lines.append(f"  배당성향: {self.dividend_payout:.1f}%")
        if self.trends:
            lines.append(
                f"  트렌드: {', '.join(f'{k}={v:+.2f}%p/yr' for k, v in self.trends.items() if abs(v) > 0.01)}"
            )
        if self.warnings:
            for w in self.warnings:
                lines.append(f"  ⚠ {w}")
        return "\n".join(lines)


@dataclass
class ProFormaYear:
    """단일 연도 pro-forma — IS + BS + CF 전체."""

    year_offset: int  # +1, +2, ... +5

    # IS
    revenue: float = 0
    cogs: float = 0
    gross_profit: float = 0
    sga: float = 0
    depreciation: float = 0
    operating_income: float = 0
    interest_expense: float = 0
    ebt: float = 0
    tax: float = 0
    net_income: float = 0
    ebitda: float = 0

    # BS
    cash: float = 0
    receivables: float = 0
    inventories: float = 0
    other_current_assets: float = 0
    current_assets: float = 0
    ppe_net: float = 0
    other_noncurrent_assets: float = 0
    total_assets: float = 0
    payables: float = 0
    short_term_debt: float = 0
    other_current_liabilities: float = 0
    current_liabilities: float = 0
    long_term_debt: float = 0
    other_noncurrent_liabilities: float = 0
    total_liabilities: float = 0
    retained_earnings: float = 0
    total_equity: float = 0

    # CF
    ocf: float = 0
    capex: float = 0
    fcf: float = 0
    dividends: float = 0
    financing_cf: float = 0
    net_cash_change: float = 0

    # 검증
    bs_balanced: bool = True


@dataclass
class ProFormaResult:
    """3-statement pro-forma 전체 결과."""

    historical_ratios: HistoricalRatios
    base_year: dict[str, float]
    projections: list[ProFormaYear]
    scenario_name: str
    revenue_growth_path: list[float]
    wacc: float
    wacc_details: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    DISCLAIMER: str = "본 분석은 투자 참고용이며 투자 권유가 아닙니다."

    def __repr__(self) -> str:
        lines = [f"[Pro-Forma 재무제표 — {self.scenario_name}]"]
        lines.append(f"  WACC: {self.wacc:.1f}%")
        lines.append(f"  성장률: {' → '.join(f'{g:+.1f}%' for g in self.revenue_growth_path)}")
        lines.append("")

        # IS 요약
        lines.append("  === 손익계산서 (IS) ===")
        lines.append("  연도   |    매출    |  영업이익  |  순이익   | EBITDA")
        lines.append("  -------|-----------|-----------|----------|----------")
        for p in self.projections:
            lines.append(
                f"  +{p.year_offset}년  | {p.revenue / 1e8:>9,.0f}억 | {p.operating_income / 1e8:>9,.0f}억 "
                f"| {p.net_income / 1e8:>8,.0f}억 | {p.ebitda / 1e8:>8,.0f}억"
            )

        # BS 요약
        lines.append("")
        lines.append("  === 대차대조표 (BS) ===")
        lines.append("  연도   |   총자산   |  총부채   |  총자본   |  현금")
        lines.append("  -------|-----------|----------|----------|----------")
        for p in self.projections:
            bal = "✓" if p.bs_balanced else "✗"
            lines.append(
                f"  +{p.year_offset}년  | {p.total_assets / 1e8:>9,.0f}억 | {p.total_liabilities / 1e8:>8,.0f}억 "
                f"| {p.total_equity / 1e8:>8,.0f}억 | {p.cash / 1e8:>8,.0f}억 {bal}"
            )

        # CF 요약
        lines.append("")
        lines.append("  === 현금흐름표 (CF) ===")
        lines.append("  연도   |    OCF    |   CAPEX   |   FCF    |  배당")
        lines.append("  -------|-----------|-----------|----------|----------")
        for p in self.projections:
            lines.append(
                f"  +{p.year_offset}년  | {p.ocf / 1e8:>9,.0f}억 | {p.capex / 1e8:>9,.0f}억 "
                f"| {p.fcf / 1e8:>8,.0f}억 | {p.dividends / 1e8:>8,.0f}억"
            )

        if self.warnings:
            lines.append("")
            for w in self.warnings:
                lines.append(f"  ⚠ {w}")
        lines.append(f"\n  ※ {self.DISCLAIMER}")
        return "\n".join(lines)


# ══════════════════════════════════════
# 유틸
# ══════════════════════════════════════


def _median(values: list[float]) -> float:
    """순수 Python 중위값."""
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2


def _remove_outliers_iqr(values: list[float]) -> list[float]:
    """IQR 기반 이상치 제거 (Q1 - 1.5×IQR ~ Q3 + 1.5×IQR)."""
    if len(values) < 4:
        return values
    s = sorted(values)
    n = len(s)
    q1 = s[n // 4]
    q3 = s[3 * n // 4]
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return [v for v in values if lower <= v <= upper]


def _weighted_ratio(values: list[float]) -> tuple[float, float]:
    """최근 가중 비율 + 연간 트렌드 기울기.

    v2 Adaptive Ratio: 정적 중위값 대신 최근 데이터에 높은 가중치를 두고,
    방향성(트렌드)도 함께 추출한다.

    Returns:
        (weighted_value, trend_per_year)
    """
    if not values:
        return 0.0, 0.0
    if len(values) == 1:
        return values[0], 0.0

    # IQR 이상치 제거 — 원본 순서 유지를 위해 인덱스 기반
    cleaned = _remove_outliers_iqr(values)
    if not cleaned:
        cleaned = values

    # 최근 가중 평균 (최근일수록 높은 가중치)
    # 2개: [0.35, 0.65], 3개: [0.15, 0.30, 0.55], 4개: [0.10, 0.15, 0.30, 0.45], 5+개: [0.05, 0.10, 0.15, 0.25, 0.45]
    n = len(cleaned)
    if n == 2:
        weights = [0.35, 0.65]
    elif n == 3:
        weights = [0.15, 0.30, 0.55]
    elif n == 4:
        weights = [0.10, 0.15, 0.30, 0.45]
    else:
        # 5+ 데이터: 마지막 5개만 사용
        cleaned = cleaned[-5:]
        weights = [0.05, 0.10, 0.15, 0.25, 0.45]
        n = len(cleaned)
        weights = weights[-n:]

    # 가중치 정규화
    w_sum = sum(weights)
    weights = [w / w_sum for w in weights]

    weighted_val = sum(v * w for v, w in zip(cleaned, weights))

    # 트렌드: 마지막 3년 평균 - 처음 3년 평균 → 연간 기울기
    trend = 0.0
    if n >= 3:
        first_half = cleaned[: max(1, n // 2)]
        second_half = cleaned[max(1, n // 2) :]
        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)
        span = max(1, n - 1)
        trend = (avg_second - avg_first) / span

    return weighted_val, trend


def _annual_ttm_values(series: dict, sj: str, key: str, n: int) -> list[float]:
    """최근 N년간 연간 합산값(TTM 방식) 리스트.

    분기별 시계열에서 4분기 단위 rolling TTM을 역순으로 N개 추출.
    """
    vals = series.get(sj, {}).get(key, [])
    if not vals:
        return []
    results = []
    for end in range(len(vals), 3, -4):
        chunk = [v for v in vals[end - 4 : end] if v is not None]
        if len(chunk) == 4:
            results.append(sum(chunk))
        if len(results) >= n:
            break
    results.reverse()
    return results


def _annual_latest_values(series: dict, sj: str, key: str, n: int) -> list[float]:
    """최근 N년간 BS 최신값 리스트 (분기 말 잔액)."""
    vals = series.get(sj, {}).get(key, [])
    if not vals:
        return []
    results = []
    for end in range(len(vals), 0, -4):
        chunk = [v for v in vals[max(0, end - 4) : end] if v is not None]
        if chunk:
            results.append(chunk[-1])
        if len(results) >= n:
            break
    results.reverse()
    return results


def _safe_ratio_list(num_vals: list[float], den_vals: list[float], *, pct: bool = True) -> list[float]:
    """두 값 리스트의 비율 리스트 (% 변환 옵션)."""
    ratios = []
    for n, d in zip(num_vals, den_vals):
        if d and abs(d) > 1e-12:
            r = n / d
            if pct:
                r *= 100
            ratios.append(r)
    return ratios


# ══════════════════════════════════════
# 과거 비율 추출
# ══════════════════════════════════════


def _ehrCollectSeries(series: dict, n: int) -> dict[str, list]:
    """IS/CF/BS 10+ 계정 시계열 일괄 수집. 반환: {key: list[float]}."""

    def ttm(sj: str, acc: str) -> list:
        return _annual_ttm_values(series, sj, acc, n)

    def bs(acc: str) -> list:
        return _annual_latest_values(series, "BS", acc, n)

    return {
        "rev": ttm("IS", "sales"),
        "gp": ttm("IS", "gross_profit"),
        "sga": ttm("IS", "selling_and_administrative_expenses"),
        "pbt": ttm("IS", "profit_before_tax"),
        "tax": ttm("IS", "income_tax_expense"),
        "fc": ttm("IS", "finance_costs") or ttm("IS", "interest_expense"),
        "ni": ttm("IS", "net_profit") or ttm("IS", "net_income"),
        "op": ttm("IS", "operating_profit") or ttm("IS", "operating_income"),
        "dep": (
            ttm("CF", "depreciation_and_amortization")
            or ttm("CF", "depreciation_cf")
            or ttm("IS", "depreciation_and_amortization")
            or ttm("IS", "depreciation")
        ),
        "capex": ttm("CF", "purchase_of_property_plant_and_equipment"),
        "div": ttm("CF", "dividends_paid"),
        "ca": bs("current_assets"),
        "cl": bs("current_liabilities"),
        "cash": bs("cash_and_cash_equivalents"),
        "stb": bs("shortterm_borrowings"),
        "ltb": bs("longterm_borrowings"),
        "bond": bs("debentures"),
        "ar": bs("trade_receivables") or bs("trade_and_other_receivables"),
        "inv": bs("inventories"),
        "ap": bs("trade_payables") or bs("trade_and_other_payables"),
    }


def _ehrDepInSga(s: dict) -> bool:
    """K-IFRS IS 구조 감지 — D&A 가 SGA 에 포함되었는지 (최근 3년 gap<2%p)."""
    gp, sga, op, rev = s["gp"], s["sga"], s["op"], s["rev"]
    if not (gp and sga and op):
        return False
    check_n = min(3, len(gp), len(sga), len(op), len(rev))
    if check_n < 1:
        return False
    matches = 0
    for j in range(check_n):
        idx = -(j + 1)
        if rev[idx] and rev[idx] > 0:
            gap_pct = abs((gp[idx] - sga[idx] - op[idx]) / rev[idx]) * 100
            if gap_pct < 2.0:
                matches += 1
    return matches >= max(1, check_n - 1)


def _ehrInterestRate(s: dict) -> float:
    """FC / 총차입금 가중 비율. 기본 4%."""
    debt_totals: list[float] = []
    for i in range(min(len(s["stb"]), len(s["ltb"]))):
        d = (
            (s["stb"][i] if i < len(s["stb"]) else 0)
            + (s["ltb"][i] if i < len(s["ltb"]) else 0)
            + (s["bond"][i] if i < len(s["bond"]) else 0)
        )
        debt_totals.append(d)
    int_ratios: list[float] = []
    for fc_v, d_v in zip(s["fc"], debt_totals):
        if d_v and d_v > 0 and fc_v:
            r = abs(fc_v) / d_v * 100
            if 0 < r < 30:
                int_ratios.append(r)
    return _weighted_ratio(int_ratios)[0] if int_ratios else 4.0


def _ehrNwcRatio(s: dict, trends: dict) -> float:
    """순운전자본 / 매출 가중 비율. 기본 10%."""
    nwc_ratios: list[float] = []
    for i in range(min(len(s["ca"]), len(s["cl"]), len(s["cash"]), len(s["rev"]))):
        nwc = s["ca"][i] - s["cl"][i] - s["cash"][i]
        if s["rev"][i] and abs(s["rev"][i]) > 0:
            nwc_ratios.append(nwc / s["rev"][i] * 100)
    if nwc_ratios:
        ratio, trends["nwc_to_revenue"] = _weighted_ratio(nwc_ratios)
        return ratio
    return 10.0


def _ehrPayoutRatio(s: dict) -> float:
    """배당성향 가중 비율 (0 < p < 200). 기본 0%."""
    payout_ratios: list[float] = []
    for dv, ni in zip(s["div"], s["ni"]):
        if ni and ni > 0 and dv:
            p = abs(dv) / ni * 100
            if 0 < p < 200:
                payout_ratios.append(p)
    return _weighted_ratio(payout_ratios)[0] if payout_ratios else 0.0


def _ehrWeightedOrDefault(ratios: list[float], default: float, trends: dict, trend_key: str) -> float:
    """_weighted_ratio(ratios) 계산. 비어있으면 default. trend 는 trends[trend_key] 에 저장."""
    if not ratios:
        return default
    val, trend = _weighted_ratio(ratios)
    trends[trend_key] = trend
    return val


def _ehrDepreciationRatio(s: dict, capex_ratio: float, trends: dict) -> tuple[float, list[str]]:
    """감가상각/매출 비율 계산 — D&A 시계열 없으면 CAPEX×80% 추정. 반환: (비율, warnings)."""
    dep_list = _safe_ratio_list(s["dep"], s["rev"]) if s["dep"] else []
    warnings: list[str] = []
    if dep_list:
        ratio, trends["depreciation_ratio"] = _weighted_ratio(dep_list)
        return ratio, warnings
    if capex_ratio > 0:
        ratio = capex_ratio * 0.8
        warnings.append(f"감가상각 데이터 없음 — CAPEX×80% 추정 ({ratio:.1f}%)")
        return ratio, warnings
    return 3.0, warnings


def _ehrBuildWarnings(s: dict, actual_years: int, capex_ratio: float) -> list[str]:
    """기본값 사용 / 저신뢰 경고 문자열 리스트."""
    warnings: list[str] = []
    if actual_years < 2:
        warnings.append("과거 데이터 2년 미만 — 비율 신뢰도 낮음")
    if not s["gp"]:
        warnings.append("매출총이익 데이터 없음 — 기본값 30% 사용")
    if not s["sga"]:
        warnings.append("판관비 데이터 없음 — 기본값 15% 사용")
    if not s["dep"] and capex_ratio <= 0:
        warnings.append("감가상각 데이터 없음 — 기본값 3% 사용")
    if not s["capex"]:
        warnings.append("CAPEX 데이터 없음 — 기본값 5% 사용")
    return warnings


def extract_historical_ratios(
    series: dict,
    years: int = 5,
) -> HistoricalRatios:
    """과거 시계열에서 구조적 비율을 중위값으로 추출 orchestrator (Q3.1f split).

    Parameters
    ----------
    series : dict
        {sjDiv: {accountNm: list[float]}} 형태의 시계열.
    years : int
        과거 몇 년치를 사용할지 (기본 5).

    Returns
    -------
    HistoricalRatios
        gross_margin/sga_ratio/effective_tax_rate/depreciation_ratio/
        interest_rate_on_debt/nwc_to_revenue/capex_to_revenue/dividend_payout/
        receivables_to_revenue/inventory_to_revenue/payables_to_revenue (모두 %)
        years_used : int, confidence : str, dep_in_sga : bool,
        warnings : list[str], trends : dict[str, float]
    """
    s = _ehrCollectSeries(series, years)
    trends: dict[str, float] = {}
    actual_years = len(s["rev"])

    gross_margin = _ehrWeightedOrDefault(
        _safe_ratio_list(s["gp"], s["rev"]) if s["gp"] else [], 30.0, trends, "gross_margin"
    )
    sga_ratio = _ehrWeightedOrDefault(
        _safe_ratio_list(s["sga"], s["rev"]) if s["sga"] else [], 15.0, trends, "sga_ratio"
    )
    capex_list = [abs(c) / r * 100 for c, r in zip(s["capex"], s["rev"]) if r > 0] if s["capex"] else []
    capex_ratio = _ehrWeightedOrDefault(capex_list, 5.0, trends, "capex_to_revenue")

    dep_ratio, warnings_extra = _ehrDepreciationRatio(s, capex_ratio, trends)
    dep_in_sga = _ehrDepInSga(s)
    if dep_in_sga:
        warnings_extra.append("IS 구조 감지: D&A가 SGA에 포함 — 별도 차감 생략 (EBITDA 계산에만 사용)")

    tax_ratios_raw = _safe_ratio_list(s["tax"], s["pbt"]) if s["tax"] and s["pbt"] else []
    effective_tax = _ehrWeightedOrDefault([t for t in tax_ratios_raw if 0 < t < 50], 22.0, trends, "effective_tax_rate")

    interest_rate = _ehrInterestRate(s)
    nwc_ratio = _ehrNwcRatio(s, trends)

    ar_list = _safe_ratio_list(s["ar"], s["rev"][: len(s["ar"])]) if s["ar"] else []
    inv_list = _safe_ratio_list(s["inv"], s["rev"][: len(s["inv"])]) if s["inv"] else []
    ap_list = _safe_ratio_list(s["ap"], s["rev"][: len(s["ap"])]) if s["ap"] else []
    ar_ratio = _weighted_ratio(ar_list)[0] if ar_list else 15.0
    inv_ratio = _weighted_ratio(inv_list)[0] if inv_list else 10.0
    ap_ratio = _weighted_ratio(ap_list)[0] if ap_list else 8.0

    payout = _ehrPayoutRatio(s)
    confidence = "high" if actual_years >= 4 else "medium" if actual_years >= 2 else "low"
    warnings = _ehrBuildWarnings(s, actual_years, capex_ratio) + warnings_extra

    return HistoricalRatios(
        gross_margin=gross_margin,
        sga_ratio=sga_ratio,
        effective_tax_rate=effective_tax,
        depreciation_ratio=dep_ratio,
        interest_rate_on_debt=interest_rate,
        nwc_to_revenue=nwc_ratio,
        capex_to_revenue=capex_ratio,
        dividend_payout=payout,
        receivables_to_revenue=ar_ratio,
        inventory_to_revenue=inv_ratio,
        payables_to_revenue=ap_ratio,
        years_used=actual_years,
        confidence=confidence,
        dep_in_sga=dep_in_sga,
        warnings=warnings,
        trends=trends,
    )


# ══════════════════════════════════════
# 개별 Beta (주가 수익률 회귀)
# ══════════════════════════════════════


@functools.lru_cache(maxsize=128)
def _fetchBeta(stockCode: str, currency: str = "KRW") -> float | None:
    """1년 일별 수익률 vs 시장 지수 회귀로 Beta 산출.

    [성능] @lru_cache 적용 — review에서 6번 호출되는데 매번 외부 API.
    같은 stockCode 입력은 첫 호출 후 즉시 반환.
    """
    try:
        import httpx

        from dartlab.gather.http import run_async

        async def _calc():
            async with httpx.AsyncClient(timeout=15) as client:
                if currency == "KRW":
                    from dartlab.gather.domains.naver import fetch_history

                    stockHist = await fetch_history(stockCode, client, market="KR")
                    marketHist = await fetch_history("KOSPI", client, market="KR")
                else:
                    return None

                if len(stockHist) < 250 or len(marketHist) < 250:
                    return None

                # 최근 1년(약 250 거래일)만 사용
                stockHist = stockHist[-260:]
                marketHist = marketHist[-260:]

                import polars as pl

                sdf = pl.DataFrame(stockHist).select(
                    pl.col("date").cast(pl.Date).alias("date"),
                    pl.col("close").cast(pl.Float64).alias("sc"),
                )
                mdf = pl.DataFrame(marketHist).select(
                    pl.col("date").cast(pl.Date).alias("date"),
                    pl.col("close").cast(pl.Float64).alias("mc"),
                )
                joined = sdf.join(mdf, on="date", how="inner").sort("date")
                if joined.height < 60:
                    return None

                joined = joined.with_columns(
                    (pl.col("sc") / pl.col("sc").shift(1) - 1).alias("sr"),
                    (pl.col("mc") / pl.col("mc").shift(1) - 1).alias("mr"),
                ).drop_nulls()

                if joined.height < 30:
                    return None

                sr = joined["sr"].to_numpy()
                mr = joined["mr"].to_numpy()
                cov = (sr * mr).mean() - sr.mean() * mr.mean()
                var = mr.var()
                if var is None or var == 0:
                    return None
                beta = float(cov / var)
                return round(max(0.3, min(beta, 3.0)), 2)

        return run_async(_calc())
    except (ImportError, OSError, RuntimeError, AttributeError):
        return None


# 회사 고유 WACC
# ══════════════════════════════════════


def _resolveCountryFromCurrency(currency: str) -> str:
    """currency → ISO2 fallback. riskPremiums.resolveCountryCode 재사용."""
    try:
        from dartlab.macro.riskPremiums import resolveCountryCode

        return resolveCountryCode(currency=currency)
    except ImportError:
        return "KR"


def compute_company_wacc(
    series: dict,
    sector_params=None,
    sector_elasticity: SectorElasticity | None = None,
    risk_free_rate: float | None = None,
    market_premium: float | None = None,
    market_cap: float | None = None,
    currency: str = "KRW",
    beta_override: float | None = None,
    country: str | None = None,
    country_risk_premium: float | None = None,
    implied_erp: bool = False,
    bottom_up_beta: bool = False,
) -> tuple[float, dict[str, float]]:
    """회사 고유 WACC 계산 (Damodaran CAPM 기반).

    Ke = Rf + beta * (matureMarketERP + countryRiskPremium)
    WACC = E/(D+E) * Ke + D/(D+E) * Kd * (1-t)

    Parameters
    ----------
    country : ISO2 국가코드 (KR/US/JP/...). 지정 시 Damodaran 테이블로 rf/erp 자동.
              None 이면 기존 `getMarketParams(currency)` 경로 (backward compat).
    country_risk_premium : 국가 리스크 프리미엄 (%) 명시 override. None 이면 자동.
    implied_erp : True 면 Damodaran Gordon 역산 (시장 내재). 실패 시 historical fallback.
    bottom_up_beta : True 면 섹터 peer unlever/relever (Hamada). 실패 시 기본 beta.
    """
    from dartlab.core.sector import getMarketParams

    damodaran = None
    if country or country_risk_premium is not None or implied_erp:
        if implied_erp:
            from dartlab.macro.impliedERP import calcImpliedERP

            damodaran = calcImpliedERP(country=country or _resolveCountryFromCurrency(currency))
        else:
            from dartlab.macro.riskPremiums import loadDamodaranERP

            damodaran = loadDamodaranERP(countryCode=country, currency=currency)

    mkt = getMarketParams(currency)
    if risk_free_rate is not None:
        rf = risk_free_rate
    elif damodaran is not None:
        rf = damodaran["riskFreeRate"]
    else:
        rf = mkt.riskFreeRate

    if market_premium is not None:
        erp = market_premium
    elif damodaran is not None:
        base_erp = damodaran["matureMarketERP"]
        crp = country_risk_premium if country_risk_premium is not None else damodaran["countryRiskPremium"]
        erp = base_erp + crp
    else:
        erp = mkt.totalErp

    # beta: 1순위 외부 주입, 2순위 bottom-up peer Hamada, 3순위 섹터 파라미터, 4순위 1.0
    beta = beta_override
    if beta is None and bottom_up_beta:
        try:
            from dartlab.core.finance.bottomUpBeta import calcBottomUpBeta

            stb_bu = getLatest(series, "BS", "shortterm_borrowings") or 0
            ltb_bu = getLatest(series, "BS", "longterm_borrowings") or 0
            bonds_bu = getLatest(series, "BS", "debentures") or 0
            debt_bu = stb_bu + ltb_bu + bonds_bu
            equity_bu = getLatest(series, "BS", "total_stockholders_equity") or getLatest(
                series, "BS", "owners_of_parent_equity"
            )
            de_bu = (debt_bu / equity_bu) if (equity_bu and equity_bu > 0) else 0.3
            sector_name = sector_params.name if sector_params and hasattr(sector_params, "name") else "Unknown"
            bu_result = calcBottomUpBeta(
                sector=sector_name,
                debtToEquity=de_bu,
                taxRate=0.22,
                country=country or _resolveCountryFromCurrency(currency),
            )
            if bu_result.get("leveredBeta"):
                beta = bu_result["leveredBeta"]
        except (ImportError, AttributeError, ValueError, TypeError):
            pass
    if beta is None:
        if sector_params and hasattr(sector_params, "beta") and sector_params.beta:
            beta = sector_params.beta
        elif sector_elasticity and hasattr(sector_elasticity, "revenueToGdp"):
            beta = max(0.5, min(sector_elasticity.revenueToGdp, 2.5))
        else:
            beta = 1.0

    # 시가총액 기반 beta 감쇠 — 대형주는 시장 대비 변동성이 낮음
    if market_cap and market_cap > 0:
        mcTrillion = market_cap / 1e12
        if mcTrillion > 50:
            beta *= 0.8
        elif mcTrillion > 10:
            beta *= 0.9

    # 차입금
    stb = getLatest(series, "BS", "shortterm_borrowings") or 0
    ltb = getLatest(series, "BS", "longterm_borrowings") or 0
    bonds = getLatest(series, "BS", "debentures") or 0
    total_debt = stb + ltb + bonds

    # 자기자본 = 시가총액 or 장부가
    equity_book = getLatest(series, "BS", "total_stockholders_equity") or getLatest(
        series, "BS", "owners_of_parent_equity"
    )
    equity_value = market_cap if market_cap else (equity_book or 1)

    # Kd (타인자본비용) -- 실제 이자비용 역산
    fc = getTTM(series, "IS", "finance_costs") or getTTM(series, "IS", "interest_expense")
    if fc and total_debt > 0:
        kd = abs(fc) / total_debt * 100
        kd = max(2.0, min(kd, 15.0))
    else:
        kd = rf + 1.0  # Rf + 1%p 스프레드 (기존 4.0% 하드코딩 제거)

    # Ke (자기자본비용) -- CAPM: Rf + beta * (ERP + CRP)
    ke = rf + beta * erp

    # 유효세율
    pbt = getTTM(series, "IS", "profit_before_tax")
    tax_exp = getTTM(series, "IS", "income_tax_expense")
    if pbt and tax_exp and pbt > 0:
        tax_rate = min(abs(tax_exp) / pbt, 0.5)
    else:
        tax_rate = mkt.defaultTaxRate / 100

    # WACC
    total_capital = equity_value + total_debt
    if total_capital > 0:
        e_weight = equity_value / total_capital
        d_weight = total_debt / total_capital
    else:
        e_weight, d_weight = 1.0, 0.0

    wacc = e_weight * ke + d_weight * kd * (1 - tax_rate)
    # Phase 4 G12.1: 대기업 AA급 현실 (Rf 2.4% + 1.5%p ≈ 4%) 반영 — 하한 5→4
    wacc = max(4.0, min(wacc, 20.0))

    details = {
        "ke": ke,
        "kd": kd,
        "beta": beta,
        "rf": rf,
        "erp": erp,
        "tax_rate": tax_rate * 100,
        "equity_weight": e_weight * 100,
        "debt_weight": d_weight * 100,
        "total_debt": total_debt,
        "equity_value": equity_value,
    }
    if damodaran is not None:
        details["countryCode"] = damodaran["countryCode"]
        details["countryRiskPremium"] = damodaran["countryRiskPremium"]
        details["matureMarketERP"] = damodaran["matureMarketERP"]
        details["erpSource"] = damodaran["source"]
    return wacc, details


# ══════════════════════════════════════
# 3-Statement Pro-Forma 생성
# ══════════════════════════════════════


def _extract_base_year(series: dict) -> dict[str, float]:
    """현재(기준) 연도 실적 스냅샷 추출."""
    rev = getTTM(series, "IS", "sales") or 0
    gp = getTTM(series, "IS", "gross_profit")
    oi = getTTM(series, "IS", "operating_profit") or getTTM(series, "IS", "operating_income") or 0
    ni = getTTM(series, "IS", "net_profit") or getTTM(series, "IS", "net_income") or 0

    ca = getLatest(series, "BS", "current_assets") or 0
    cl = getLatest(series, "BS", "current_liabilities") or 0
    cash = getLatest(series, "BS", "cash_and_cash_equivalents") or 0
    ta = getLatest(series, "BS", "total_assets") or 0
    tl = getLatest(series, "BS", "total_liabilities") or 0
    te = getLatest(series, "BS", "total_stockholders_equity") or getLatest(series, "BS", "owners_of_parent_equity") or 0
    ppe = getLatest(series, "BS", "tangible_assets") or 0
    ar = getLatest(series, "BS", "trade_receivables") or getLatest(series, "BS", "trade_and_other_receivables") or 0
    inv = getLatest(series, "BS", "inventories") or 0
    ap = getLatest(series, "BS", "trade_payables") or getLatest(series, "BS", "trade_and_other_payables") or 0
    stb = getLatest(series, "BS", "shortterm_borrowings") or 0
    ltb = getLatest(series, "BS", "longterm_borrowings") or 0
    bonds = getLatest(series, "BS", "debentures") or 0

    return {
        "revenue": rev,
        "gross_profit": gp,
        "operating_income": oi,
        "net_income": ni,
        "current_assets": ca,
        "current_liabilities": cl,
        "cash": cash,
        "total_assets": ta,
        "total_liabilities": tl,
        "total_equity": te,
        "ppe_net": ppe,
        "receivables": ar,
        "inventories": inv,
        "payables": ap,
        "short_term_debt": stb,
        "long_term_debt": ltb + bonds,
        "total_debt": stb + ltb + bonds,
    }


def build_proforma(
    series: dict,
    revenue_growth_path: list[float],
    sector_params=None,
    sector_elasticity: SectorElasticity | None = None,
    shares: int | None = None,
    market_cap: float | None = None,
    scenario_name: str = "base",
    overrides: dict[str, float] | None = None,
) -> ProFormaResult:
    """3-statement pro-forma 생성.

    Args:
        series: 시계열 dict.
        revenue_growth_path: 연도별 매출 성장률 (%), 예: [5.0, 4.0, 3.5]
        sector_params: SectorParams (WACC 계산용).
        shares: 발행주식수.
        market_cap: 시가총액.
        scenario_name: 시나리오 이름.
        overrides: 비율 오버라이드 (예: {"gross_margin": 35.0}).
    """
    warnings: list[str] = []

    # 1. 과거 비율 추출
    ratios = extract_historical_ratios(series)
    warnings.extend(ratios.warnings)

    # 오버라이드 적용
    if overrides:
        for k, v in overrides.items():
            if hasattr(ratios, k):
                setattr(ratios, k, v)

    # 2. WACC 계산
    wacc, wacc_details = compute_company_wacc(
        series,
        sector_params=sector_params,
        sector_elasticity=sector_elasticity,
        market_cap=market_cap,
    )

    # 3. 기준연도 추출
    base = _extract_base_year(series)
    if base["revenue"] <= 0:
        warnings.append("기준 매출이 0 — pro-forma 불가")
        return ProFormaResult(
            historical_ratios=ratios,
            base_year=base,
            projections=[],
            scenario_name=scenario_name,
            revenue_growth_path=revenue_growth_path,
            wacc=wacc,
            wacc_details=wacc_details,
            warnings=warnings,
        )

    # 4. 연도별 pro-forma 생성
    projections: list[ProFormaYear] = []
    prev_revenue = base["revenue"]
    prev_ppe = base["ppe_net"]
    base["cash"]
    prev_equity = base["total_equity"]
    prev_stb = base["short_term_debt"]
    prev_ltb = base["long_term_debt"]
    prev_nwc = base["receivables"] + base["inventories"] - base["payables"]
    prev_other_ca = base["current_assets"] - base["cash"] - base["receivables"] - base["inventories"]
    prev_other_nca = base["total_assets"] - base["current_assets"] - base["ppe_net"]
    prev_other_cl = base["current_liabilities"] - base["payables"] - base["short_term_debt"]
    prev_other_ncl = base["total_liabilities"] - base["current_liabilities"] - base["long_term_debt"]

    # 음수 보정
    prev_other_ca = max(prev_other_ca, 0)
    prev_other_nca = max(prev_other_nca, 0)
    prev_other_cl = max(prev_other_cl, 0)
    prev_other_ncl = max(prev_other_ncl, 0)

    # v2: 비율 트렌드 경로 — 연도별 비율이 트렌드 방향으로 점진 변화
    def _ratio_for_year(
        base_val: float, trend_key: str, yr_idx: int, floor: float = 0.0, ceiling: float = 100.0
    ) -> float:
        trend = ratios.trends.get(trend_key, 0.0)
        val = base_val + trend * yr_idx
        return max(floor, min(val, ceiling))

    for i, growth_pct in enumerate(revenue_growth_path):
        yr = ProFormaYear(year_offset=i + 1)

        # v2: 연도별 비율 (트렌드 반영)
        yr_gm = _ratio_for_year(ratios.gross_margin, "gross_margin", i, floor=5.0, ceiling=90.0)
        yr_sga = _ratio_for_year(ratios.sga_ratio, "sga_ratio", i, floor=1.0, ceiling=50.0)
        yr_dep = _ratio_for_year(ratios.depreciation_ratio, "depreciation_ratio", i, floor=0.5, ceiling=30.0)
        yr_capex = _ratio_for_year(ratios.capex_to_revenue, "capex_to_revenue", i, floor=0.5, ceiling=40.0)

        # === IS ===
        yr.revenue = prev_revenue * (1 + growth_pct / 100)
        yr.cogs = yr.revenue * (1 - yr_gm / 100)
        yr.gross_profit = yr.revenue - yr.cogs
        yr.sga = yr.revenue * yr_sga / 100
        yr.depreciation = yr.revenue * yr_dep / 100

        # v3: IS 구조 분기 — D&A가 SGA에 포함된 경우 별도 차감하지 않음
        if ratios.dep_in_sga:
            # SGA에 이미 D&A 포함 → OP = GP - SGA (depreciation은 EBITDA 역산에만 사용)
            yr.operating_income = yr.gross_profit - yr.sga
        else:
            # D&A 별도 보고 → OP = GP - SGA - D&A
            yr.operating_income = yr.gross_profit - yr.sga - yr.depreciation
        yr.ebitda = yr.operating_income + yr.depreciation

        # 이자비용 = 전기 차입금 × 이자율
        total_prev_debt = prev_stb + prev_ltb
        yr.interest_expense = total_prev_debt * ratios.interest_rate_on_debt / 100

        yr.ebt = yr.operating_income - yr.interest_expense
        if yr.ebt > 0:
            yr.tax = yr.ebt * ratios.effective_tax_rate / 100
        else:
            yr.tax = 0  # 적자 시 세금 없음
        yr.net_income = yr.ebt - yr.tax

        # === BS ===
        # 운전자본 항목 (매출 비례)
        yr.receivables = yr.revenue * ratios.receivables_to_revenue / 100
        yr.inventories = yr.revenue * ratios.inventory_to_revenue / 100
        yr.payables = yr.revenue * ratios.payables_to_revenue / 100

        # CAPEX & PPE
        yr.capex = -(yr.revenue * yr_capex / 100)  # 음수
        yr.ppe_net = prev_ppe + abs(yr.capex) - yr.depreciation

        # 부채 초기값 (시나리오 기본: 변동 없음)
        yr.short_term_debt = prev_stb
        yr.long_term_debt = prev_ltb

        # 기타 항목 (비례 or 유지)
        yr.other_current_assets = prev_other_ca * (1 + growth_pct / 100 * 0.3)  # 매출 연동 30%
        yr.other_noncurrent_assets = prev_other_nca

        yr.other_current_liabilities = prev_other_cl * (1 + growth_pct / 100 * 0.3)
        yr.other_noncurrent_liabilities = prev_other_ncl

        # 배당
        if yr.net_income > 0:
            yr.dividends = yr.net_income * ratios.dividend_payout / 100
        else:
            yr.dividends = 0

        # 자본 = 전기 자본 + 순이익 - 배당
        yr.retained_earnings = prev_equity + yr.net_income - yr.dividends
        yr.total_equity = yr.retained_earnings

        # 부채 합계
        yr.current_liabilities = yr.payables + yr.short_term_debt + yr.other_current_liabilities
        yr.total_liabilities = yr.current_liabilities + yr.long_term_debt + yr.other_noncurrent_liabilities

        # Cash = plug (총자산 = 총부채 + 총자본 이므로, 나머지 자산의 차이)
        non_cash_assets = (
            yr.receivables + yr.inventories + yr.other_current_assets + yr.ppe_net + yr.other_noncurrent_assets
        )
        required_total_assets = yr.total_liabilities + yr.total_equity
        yr.cash = required_total_assets - non_cash_assets

        # v2: 현금 음수 → 자동 차입 (50:50 단기/장기 분배)
        if yr.cash < 0:
            shortfall = abs(yr.cash)
            # 반복 균형 (이자→순이익→자본 감소→현금 재하락 사이클 수렴)
            for _ in range(3):
                yr.short_term_debt += shortfall * 0.5
                yr.long_term_debt += shortfall * 0.5
                extra_interest = shortfall * ratios.interest_rate_on_debt / 100
                yr.interest_expense += extra_interest
                yr.ebt = yr.operating_income - yr.interest_expense
                yr.tax = yr.ebt * ratios.effective_tax_rate / 100 if yr.ebt > 0 else 0
                yr.net_income = yr.ebt - yr.tax
                yr.dividends = yr.net_income * ratios.dividend_payout / 100 if yr.net_income > 0 else 0
                yr.retained_earnings = prev_equity + yr.net_income - yr.dividends
                yr.total_equity = yr.retained_earnings
                yr.current_liabilities = yr.payables + yr.short_term_debt + yr.other_current_liabilities
                yr.total_liabilities = yr.current_liabilities + yr.long_term_debt + yr.other_noncurrent_liabilities
                required_total_assets = yr.total_liabilities + yr.total_equity
                yr.cash = required_total_assets - non_cash_assets
                if yr.cash >= 0:
                    break
                shortfall = abs(yr.cash)
            if yr.cash < 0:
                yr.cash = 0
            warnings.append(f"+{yr.year_offset}년: 현금 부족 → 자동 차입 {shortfall / 1e8:.0f}억")

        yr.current_assets = yr.cash + yr.receivables + yr.inventories + yr.other_current_assets
        yr.total_assets = yr.current_assets + yr.ppe_net + yr.other_noncurrent_assets

        # BS 균형 검증
        imbalance = abs(yr.total_assets - yr.total_liabilities - yr.total_equity)
        yr.bs_balanced = imbalance < max(1, yr.total_assets * 1e-10)

        # === CF ===
        nwc = yr.receivables + yr.inventories - yr.payables
        delta_nwc = nwc - prev_nwc

        yr.ocf = yr.net_income + yr.depreciation - delta_nwc
        yr.fcf = yr.ocf + yr.capex  # capex는 음수
        delta_debt = (yr.short_term_debt + yr.long_term_debt) - (prev_stb + prev_ltb)
        yr.financing_cf = delta_debt - yr.dividends
        yr.net_cash_change = yr.ocf + yr.capex + yr.financing_cf

        projections.append(yr)

        # 다음 연도용 이전값 갱신
        prev_revenue = yr.revenue
        prev_ppe = yr.ppe_net
        prev_equity = yr.total_equity
        prev_stb = yr.short_term_debt
        prev_ltb = yr.long_term_debt
        prev_nwc = nwc
        prev_other_ca = yr.other_current_assets
        prev_other_nca = yr.other_noncurrent_assets
        prev_other_cl = yr.other_current_liabilities
        prev_other_ncl = yr.other_noncurrent_liabilities

    # v3: 영업이익률 크로스체크 — 기준연도와 예측 1년차 괴리 감지
    if projections and base["revenue"] > 0 and base["operating_income"] > 0:
        base_opm = base["operating_income"] / base["revenue"] * 100
        proj_opm = projections[0].operating_income / projections[0].revenue * 100 if projections[0].revenue > 0 else 0
        gap = abs(proj_opm - base_opm)
        if gap > 5.0:
            warnings.append(f"영업이익률 괴리 경고: 기준 {base_opm:.1f}% → 예측 {proj_opm:.1f}% (차이 {gap:.1f}%p)")

    return ProFormaResult(
        historical_ratios=ratios,
        base_year=base,
        projections=projections,
        scenario_name=scenario_name,
        revenue_growth_path=revenue_growth_path,
        wacc=wacc,
        wacc_details=wacc_details,
        warnings=warnings,
    )

"""analysis/valuation/dcf DDM 그룹 분리.

identity 보존을 위해 dcf.py 가 본 모듈에서 re-export 한다.
"""

from __future__ import annotations

from typing import Optional

from dartlab.analysis.valuation._dcfTypes import DDMResult
from dartlab.core.utils.calc import cagr as _cagr
from dartlab.core.utils.extract import getAnnualValues, getLatest, getTTM
from dartlab.frame.sector import SectorParams

# ── DDM ──────────────────────────────────────────────


def _annualDividends(series: dict) -> list[float]:
    """분기 dividends_paid → 4분기 합산 연간 배당 리스트.

    CF/dividends_paid는 분기별 데이터가 섞여 있으므로
    4개씩 묶어 합산하여 연간 값으로 변환한다.
    부호가 혼재하므로 abs 적용 후 합산.
    이상값(전체 중앙값의 100배 초과) 제거.
    """
    raw = getAnnualValues(series, "CF", "dividends_paid")
    if not raw:
        return []

    # None 제거하고 abs 적용한 인접 데이터 추출
    absVals = [abs(v) for v in raw if v is not None]
    if not absVals:
        return []

    # 이상값 필터: 중앙값의 100배 초과 제거
    sortedVals = sorted(absVals)
    median = sortedVals[len(sortedVals) // 2] if sortedVals else 0
    if median > 0:
        absVals = [v for v in absVals if v < median * 100]

    # 4분기 합산
    annuals: list[float] = []
    for i in range(0, len(absVals) - 3, 4):
        chunk = absVals[i : i + 4]
        total = sum(chunk)
        if total > 0:
            annuals.append(total)

    # 4분기 합산이 2개 미만이면 TTM fallback
    if len(annuals) < 2:
        ttm = getTTM(series, "CF", "dividends_paid")
        if ttm is not None and abs(ttm) > 0:
            annuals = [abs(ttm)]

    return annuals


def ddmValuation(
    series: dict,
    shares: Optional[int] = None,
    sectorParams: Optional[SectorParams] = None,
    currentPrice: Optional[float] = None,
    discountRate: Optional[float] = None,
    annualDividends: Optional[list[float]] = None,
) -> DDMResult:
    """Gordon Growth / 2-Stage DDM.

    Args:
        annualDividends: 연간 배당 총액 리스트 (과거→최신 순).
            calcDividendPolicy에서 추출한 정확한 연간 합산 값 우선.
            None이면 CF/dividends_paid에서 자체 추출.
    """
    warnings: list[str] = []
    r = discountRate or (sectorParams.discountRate if sectorParams else 10.0)

    # 1순위: 외부에서 전달받은 연간 배당 (calcDividendPolicy 기반)
    # 2순위: CF/dividends_paid에서 자체 추출
    if annualDividends and len(annualDividends) >= 1:
        annualDivs = annualDividends
        latestDiv = annualDivs[-1]
    else:
        annualDivs = _annualDividends(series)
        ttmDiv = getTTM(series, "CF", "dividends_paid")
        latestDivFromTtm = abs(ttmDiv) if ttmDiv is not None and ttmDiv != 0 else None

        if annualDivs:
            latestDiv = annualDivs[-1]
        elif latestDivFromTtm and latestDivFromTtm > 0:
            latestDiv = latestDivFromTtm
            annualDivs = [latestDiv]
        else:
            latestDiv = None

    if latestDiv is None or latestDiv <= 0 or shares is None or shares <= 0:
        return DDMResult(
            intrinsicValue=None,
            dividendPerShare=None,
            dividendYield=None,
            payoutRatio=None,
            dividendGrowth=None,
            modelUsed="N/A",
            discountRate=r,
            warnings=["무배당 또는 배당 데이터 부족"],
        )

    dps = latestDiv / shares

    # 배당 성장률: 연간 합산 기준 CAGR
    divGrowth: float | None = None
    if len(annualDivs) >= 2:
        n = min(len(annualDivs), 4)
        divGrowth = _cagr(annualDivs[-n], annualDivs[-1], n - 1)

    if divGrowth is None or divGrowth > 25:
        divGrowth = min(r - 2, 5.0)
        warnings.append("배당 성장률 비정상 → 보수적 추정 적용")

    if divGrowth < 0:
        divGrowth = 0.0
        warnings.append("배당 감소 추세 → 성장률 0%로 설정")

    netIncome = getTTM(series, "IS", "net_profit") or getTTM(series, "IS", "net_income")
    payout = None
    if netIncome and netIncome > 0:
        payout = latestDiv / netIncome * 100

    divYield = None
    if currentPrice and currentPrice > 0:
        divYield = dps / currentPrice * 100

    if r / 100 <= divGrowth / 100:
        warnings.append("배당성장률 ≥ 할인율 → DDM 적용 불가")
        return DDMResult(
            intrinsicValue=None,
            dividendPerShare=dps,
            dividendYield=divYield,
            payoutRatio=payout,
            dividendGrowth=divGrowth,
            modelUsed="N/A",
            discountRate=r,
            warnings=warnings,
        )

    d1 = dps * (1 + divGrowth / 100)
    intrinsic = d1 / (r / 100 - divGrowth / 100)

    model = "gordon"
    if len(annualDivs) < 3:
        warnings.append("배당 데이터 3년 미만 → 결과 신뢰도 낮음")

    return DDMResult(
        intrinsicValue=round(intrinsic, 0),
        dividendPerShare=round(dps, 0),
        dividendYield=round(divYield, 2) if divYield is not None else None,
        payoutRatio=round(payout, 1) if payout is not None else None,
        dividendGrowth=round(divGrowth, 1),
        modelUsed=model,
        discountRate=r,
        warnings=warnings,
    )


__all__ = ["_annualDividends", "ddmValuation"]

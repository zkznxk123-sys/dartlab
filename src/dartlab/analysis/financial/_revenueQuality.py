"""revenue.py 의 매출 품질 계산 — calcRevenueQuality."""

from __future__ import annotations

from dartlab.analysis.financial._revenueSelect import _getRatios
from dartlab.core.memory import memoizedCalc


@memoizedCalc
def calcRevenueQuality(company, *, basePeriod: str | None = None) -> dict | None:
    """매출 품질 — OCF/NI 현금전환율 + 매출총이익률 추세 (4 분기).

    Capabilities:
        매출의 "품질" 진단 — OCF/NI 현금전환율 (현금 뒷받침) + 매출총이익률
        추세 (마진 개선/악화). Sloan accrual model 의 cash flow side 적용
        + 손익계산서 1 단계 마진 추세.

    Args:
        company: Company 객체.
        basePeriod: 기준 기간. None 시 최신.

    Returns:
        dict | None:
            - ``cashConversion`` (float|None): OCF/NI (%)
            - ``cashConversionLabel`` (str): "양호"/"주의"/"위험"
            - ``grossMargin`` (float|None): 매출총이익률 (%)
            - ``grossMarginTrend`` (list[float]): 최근 4 기
            - ``grossMarginDirection`` (str): "개선"/"악화"/"안정"

    Raises:
        없음.

    Example:
        >>> r = calcRevenueQuality(Company("005930"))
        >>> r["cashConversion"], r["grossMarginDirection"]
        (108, '안정')

    Guide:
        현금전환율 > 100% = 매출이 현금으로 잘 회수됨 (양호). 80~100% =
        주의 (운전자본 증가 추세 가능). < 80% = 위험 (Sloan accrual 경고).
        매출총이익률 추세 (4 분기) > +2%p 개선 또는 < -2%p 악화.

    When:
        Story revenue quality + AI 매출 품질 답변.

    How:
        ratios.operatingCfToNetIncome + grossMargin 시계열 → label/direction.

    SeeAlso:
        - ``calcEarningsMomentum``: Sloan 분해 전체 (cash + accrual)
        - ``calcMarginTrend``: 5 단계 마진 시계열
        - ``calcCashflow``: CF 분석

    Requires:
        IS + CF 시계열 + ratios.operatingCfToNetIncome.

    AIContext:
        cashConversionLabel + grossMarginDirection 함께 인용. cashConversion
        만 양호해도 grossMargin 추세 악화면 미래 위험 신호.

    LLM Specifications:
        AntiPatterns:
            - 단년도 cashConversion 만 보고 단정 — 3 년 추세 권장.
            - grossMarginDirection "안정" 도 절대 마진 수준 (예 IT 30% vs
              제조 15%) 비교 함께.
        OutputSchema:
            ``{cashConversion, cashConversionLabel, grossMargin,
            grossMarginTrend, grossMarginDirection}``.
        Prerequisites:
            IS + CF 시계열 + ratios 헬퍼.
        Freshness:
            최신 분기.
        Dataflow:
            ratios → operatingCfToNetIncome → label + grossMargin 시계열
            → direction 분류.
        TargetMarkets: KR (DART), US (EDGAR).
    """
    ratios = _getRatios(company)
    if ratios is None:
        return None

    cc = getattr(ratios, "operatingCfToNetIncome", None)
    gm = getattr(ratios, "grossMargin", None)

    if cc is None and gm is None:
        return None

    ccLabel = "양호"
    if cc is not None:
        if cc >= 80:
            ccLabel = "양호"
        elif cc >= 40:
            ccLabel = "주의"
        else:
            ccLabel = "위험"

    gmTrend: list[float] = []
    try:
        seriesResult = company._ratioSeries()
        if seriesResult is not None:
            data, _years = seriesResult
            gmSeries = data.get("RATIO", {}).get("grossMargin", [])
            if gmSeries:
                gmTrend = [v for v in gmSeries[-4:] if v is not None]
    except (ValueError, KeyError, AttributeError):
        pass

    gmDirection = "안정"
    if len(gmTrend) >= 2:
        first = gmTrend[0]
        last = gmTrend[-1]
        if first is not None and last is not None:
            diff = last - first
            if diff > 2:
                gmDirection = "개선"
            elif diff < -2:
                gmDirection = "악화"

    return {
        "cashConversion": cc,
        "cashConversionLabel": ccLabel,
        "grossMargin": gm,
        "grossMarginTrend": gmTrend,
        "grossMarginDirection": gmDirection,
    }

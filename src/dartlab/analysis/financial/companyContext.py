"""Company-bound financial analysis context helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from dartlab.core.utils.helpers import PeriodRange, annualColsFromPeriods, quarterlyColsFromPeriods

if TYPE_CHECKING:
    from dartlab.core.ratios import RatioResult


def fetchNotesDetail(company, noteKeys: list[str]) -> dict[str, list[dict]]:
    """Return note table rows for selected note keys from a Company object.

    Capabilities:
        - Company 의 notesAccessor 에서 지정 키의 DataFrame 을 dict 리스트로 반환.

    Args:
        company: Company 객체.
        noteKeys: 가져올 노트 키 리스트.

    Returns:
        dict[str, list[dict]]: 키별 행 리스트. 접근 실패 시 빈 dict.

    Guide:
        notesAccessor 가 없으면 빈 dict 반환 — 안전한 옵트인 helper.

    When:
        analysis 계열 calc 에서 주석 노트 표가 필요할 때.

    How:
        ``_notesAccessor`` 또는 ``notes`` 속성에서 각 키를 getattr → to_dicts.

    Requires:
        Company 가 notes accessor 제공.

    Raises:
        없음 (모든 예외 흡수).

    Example:
        >>> fetchNotesDetail(c, ["depreciation"])
        {"depreciation": [...]}

    SeeAlso:
        - ``getRatios``: 비율 스냅샷

    AIContext:
        AI 답변에서 주석 노트 표 인용 시.
    """

    result: dict[str, list[dict]] = {}
    notesAccessor = getattr(company, "_notesAccessor", None) or getattr(company, "notes", None)
    if notesAccessor is None:
        return result
    for key in noteKeys:
        try:
            df = getattr(notesAccessor, key, None)
            if df is not None and hasattr(df, "to_dicts"):
                result[key] = df.to_dicts()
        except (AttributeError, FileNotFoundError, ValueError, KeyError):
            pass
    return result


def getRatioSeries(company) -> tuple[dict, list[str]] | None:
    """Return ``company._ratioSeries()`` as ``(seriesData, allPeriods)`` when available.

    Requires:
        Company 가 ``_ratioSeries`` 메서드 제공.

    Raises:
        없음 (예외 흡수 후 None 반환).

    Example:
        >>> getRatioSeries(c)
        ({"roe": {...}}, ["2024Q4", ...])
    """

    try:
        result = company._ratioSeries()
        if result is None:
            return None
        return result
    except (ValueError, KeyError, AttributeError):
        return None


def getRatios(company) -> "RatioResult | None":
    """Return the Company's RatioResult object when available.

    Requires:
        Company 가 ``_finance.ratios`` 속성 제공.

    Raises:
        없음 (예외 흡수 후 None 반환).

    Example:
        >>> getRatios(c).roe
        15.3
    """

    try:
        return company._finance.ratios
    except (ValueError, KeyError, AttributeError):
        return None


def resolveBasePeriod(
    company,
    basePeriod: str | None = None,
    maxYears: int = 8,
    maxQuarters: int = 8,
) -> PeriodRange:
    """Resolve a base period against the Company's actual financial periods.

    Capabilities:
        - 입력 basePeriod (또는 최신 분기 자동) 을 기준으로 PeriodRange
          (annual + quarterly columns) 산출.

    Args:
        company: Company 객체.
        basePeriod: 기준 기간. None 시 최신 분기 자동.
        maxYears: 연도 컬럼 최대 개수.
        maxQuarters: 분기 컬럼 최대 개수.

    Returns:
        PeriodRange: basePeriod + annualCols + quarterlyCols.

    Guide:
        ratioSeries 가 비면 ``9999Q4`` fallback.

    When:
        analysis 진입점에서 표시 기간 결정 시.

    How:
        ratioSeries 의 allPeriods → 최신 분기 정렬 → annualColsFromPeriods/
        quarterlyColsFromPeriods.

    Requires:
        Company 의 ratioSeries 가용 (없으면 빈 컬럼).

    Raises:
        없음.

    Example:
        >>> resolveBasePeriod(c)
        PeriodRange(basePeriod="2024Q4", annualCols=[...], ...)

    SeeAlso:
        - ``getRatioSeries``: 입력 데이터

    AIContext:
        AI 답변에서 표시 기간 자동 결정 helper.
    """

    rs = getRatioSeries(company)
    if rs is not None:
        _, allPeriods = rs
    else:
        allPeriods = []

    if basePeriod is None:
        quarters = sorted([period for period in allPeriods if "Q" in period], reverse=True)
        resolved = quarters[0] if quarters else "9999Q4"
    else:
        resolved = basePeriod

    return PeriodRange(
        basePeriod=resolved,
        annualCols=annualColsFromPeriods(allPeriods, resolved, maxYears),
        quarterlyCols=quarterlyColsFromPeriods(allPeriods, resolved, maxQuarters),
    )

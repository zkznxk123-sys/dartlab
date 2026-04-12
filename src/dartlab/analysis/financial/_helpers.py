"""analysis 재무분석 헬퍼 — 범용 함수는 core/finance/helpers.py로 이동됨.

이 파일은 하위호환을 위한 re-export + Company 전용 함수만 포함.
신규 코드는 dartlab.core.finance.helpers를 직접 import할 것.
"""

from __future__ import annotations

# ── re-export: core/finance/helpers.py에서 이동된 범용 함수 ──
# 기존 `from dartlab.analysis.financial._helpers import toDict` 호환
from dartlab.core.finance.helpers import (  # noqa: F401
    MAX_RATIO_YEARS,
    PeriodRange,
    annualCols,
    annualColsFromPeriods,
    annualLabel,
    annualLabels,
    mergeRows,
    parseNumStr,
    periodCols,
    quarterlyCols,
    quarterlyColsFromPeriods,
    sumBorrowings,
    sumBorrowingsKorean,
    sumCostOfSales,
    sumIncomeTax,
    sumSGA,
    toDict,
    toDictBySnakeId,
)

# ── Company 전용 함수 (core로 이동 불가 — Company 객체 의존) ──


def fetchNotesDetail(company, noteKeys: list[str]) -> dict[str, list[dict]]:
    """company.notes에서 noteKeys의 DataFrame을 dict 리스트로 반환."""
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
    """ratioSeries를 안전하게 가져온다."""
    try:
        result = company._ratioSeries()
        if result is None:
            return None
        return result
    except (ValueError, KeyError, AttributeError):
        return None


def getRatios(company):
    """RatioResult 객체를 안전하게 가져온다."""
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
    """basePeriod를 Company의 실제 기간으로 해석."""
    rs = getRatioSeries(company)
    if rs is not None:
        _, allPeriods = rs
    else:
        allPeriods = []

    if basePeriod is None:
        qs = sorted([p for p in allPeriods if "Q" in p], reverse=True)
        resolved = qs[0] if qs else "9999Q4"
    else:
        resolved = basePeriod

    return PeriodRange(
        basePeriod=resolved,
        annualCols=annualColsFromPeriods(allPeriods, resolved, maxYears),
        quarterlyCols=quarterlyColsFromPeriods(allPeriods, resolved, maxQuarters),
    )

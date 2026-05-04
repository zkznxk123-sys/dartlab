"""Company-bound financial analysis context helpers."""

from __future__ import annotations

from dartlab.core.utils.helpers import PeriodRange, annualColsFromPeriods, quarterlyColsFromPeriods


def fetchNotesDetail(company, noteKeys: list[str]) -> dict[str, list[dict]]:
    """Return note table rows for selected note keys from a Company object."""

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
    """Return ``company._ratioSeries()`` as ``(seriesData, allPeriods)`` when available."""

    try:
        result = company._ratioSeries()
        if result is None:
            return None
        return result
    except (ValueError, KeyError, AttributeError):
        return None


def getRatios(company):
    """Return the Company's RatioResult object when available."""

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
    """Resolve a base period against the Company's actual financial periods."""

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

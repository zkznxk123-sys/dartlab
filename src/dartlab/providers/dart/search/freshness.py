"""Freshness normalization helpers for product search artifacts."""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

DEFAULT_DATE_COLUMNS: tuple[str, ...] = (
    "sourceDataAsOf",
    "source_data_as_of",
    "dataAsOf",
    "rcept_dt",
    "rceptDate",
    "date",
    "filing_date",
    "filed_date",
    "filingDate",
    "filedAt",
    "captured_at",
    "published",
    "acceptanceDateTime",
)


def normalizeSearchDate(value: Any) -> str:
    """Normalize a source freshness date into ``YYYYMMDD``.

    Args:
        value: Raw date-like value.

    Returns:
        str: Eight-digit date, or ``""`` when no date can be found.

    Raises:
        None.

    Example:
        >>> normalizeSearchDate("2026-06-16")
        '20260616'
    """
    raw = str(value or "").strip()
    if not raw:
        return ""
    match = re.search(r"(?:19|20)\d{2}[-/.]?\d{2}[-/.]?\d{2}", raw)
    if not match:
        return ""
    return re.sub(r"\D", "", match.group(0))[:8]


def periodToDataAsOf(period: Any) -> str:
    """Normalize ``YYYYQn`` source periods to quarter-end ``YYYYMMDD``.

    Args:
        period: Source period, such as ``"2025Q4"``.

    Returns:
        str: Quarter-end date, or ``""`` for unsupported periods.

    Raises:
        None.

    Example:
        >>> periodToDataAsOf("2025Q4")
        '20251231'
    """
    raw = str(period or "").strip().upper()
    match = re.fullmatch(r"((?:19|20)\d{2})Q([1-4])", raw)
    if not match:
        return ""
    quarterEnds = {"1": "0331", "2": "0630", "3": "0930", "4": "1231"}
    return f"{match.group(1)}{quarterEnds[match.group(2)]}"


def firstSearchDate(row: Mapping[str, Any], columns: Iterable[str] = DEFAULT_DATE_COLUMNS) -> str:
    """Return the first normalized date present in a row.

    Args:
        row: Source row mapping.
        columns: Candidate date columns in priority order.

    Returns:
        str: Normalized date or ``""``.

    Raises:
        None.

    Example:
        >>> firstSearchDate({"date": "2026-06-16"})
        '20260616'
    """
    for column in columns:
        value = normalizeSearchDate(row.get(column))
        if value:
            return value
    return ""


def sourceDataAsOfFromRow(row: Mapping[str, Any], columns: Iterable[str] = DEFAULT_DATE_COLUMNS) -> str:
    """Return source freshness from explicit date columns or ``period``.

    Args:
        row: Source row mapping.
        columns: Candidate date columns in priority order.

    Returns:
        str: Normalized source freshness.

    Raises:
        None.

    Example:
        >>> sourceDataAsOfFromRow({"period": "2025Q1"})
        '20250331'
    """
    return firstSearchDate(row, columns) or periodToDataAsOf(row.get("period"))

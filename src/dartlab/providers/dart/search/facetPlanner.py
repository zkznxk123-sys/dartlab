"""Facet planning for product search answerability."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_DART_RECEIPT_RE = re.compile(r"\b\d{14}\b")
_EDGAR_ACCESSION_RE = re.compile(r"\b\d{10}-\d{2}-\d{6}\b")
_DATE_RE = re.compile(r"\b(20\d{2})[-./년 ]?(0[1-9]|1[0-2])[-./월 ]?(0[1-9]|[12]\d|3[01])일?\b")
_YEAR_RE = re.compile(r"\b(20\d{2})년?\b")
_ASCII_LITERAL_RE = re.compile(r"\b[a-z0-9]{12,}\b")
_FRESHNESS_TERMS: tuple[str, ...] = (
    "최신",
    "최근",
    "현재",
    "오늘",
    "latest",
    "recent",
    "current",
    "newest",
    "today",
)

_REPORT_TERMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("사업보고서", ("사업보고서", "annual report", "10-k", "10k")),
    ("반기보고서", ("반기보고서", "semiannual report")),
    ("분기보고서", ("분기보고서", "quarterly report", "10-q", "10q")),
    ("주요사항보고서", ("주요사항보고서", "주요사항", "major event")),
    ("감사보고서", ("감사보고서", "audit report")),
    ("증권신고서", ("증권신고서", "registration statement")),
    ("8-K", ("8-k", "8k", "current report")),
)


@dataclass(frozen=True)
class QueryFacets:
    """Structured query constraints used after retrieval."""

    receiptNumbers: tuple[str, ...] = ()
    dates: tuple[str, ...] = ()
    years: tuple[str, ...] = ()
    reportTerms: tuple[str, ...] = ()
    literalTerms: tuple[str, ...] = ()
    stockCode: str | None = None
    corpCode: str | None = None
    companyName: str | None = None
    freshnessRequired: bool = False

    @property
    def hasConstraints(self) -> bool:
        """Return whether the query has answerability constraints.

        Returns:
            bool: True when at least one facet is present.

        Raises:
            None.

        Example:
            >>> QueryFacets(receiptNumbers=("20260615000001",)).hasConstraints
            True
        """
        return bool(
            self.receiptNumbers
            or self.dates
            or self.years
            or self.reportTerms
            or self.literalTerms
            or self.stockCode
            or self.corpCode
            or self.companyName
            or self.freshnessRequired
        )


def planQueryFacets(query: str, *, corpCode: str | None = None, stockCode: str | None = None) -> QueryFacets:
    """Extract general answerability facets from a query.

    Args:
        query: User search query.
        corpCode: Resolved DART corp code from the explicit corp argument.
        stockCode: Resolved stock code from the explicit corp argument.

    Returns:
        QueryFacets: Receipt/date/report/company constraints.

    Raises:
        None.

    Example:
        >>> planQueryFacets("20260615000001 사업보고서").receiptNumbers
        ('20260615000001',)
    """
    text = str(query or "").lower()
    receipts = tuple(dict.fromkeys(_DART_RECEIPT_RE.findall(text) + _EDGAR_ACCESSION_RE.findall(text)))
    dates = tuple(dict.fromkeys(_normalizeDate(match) for match in _DATE_RE.findall(text)))
    years = tuple(dict.fromkeys(_YEAR_RE.findall(text)))
    reports = tuple(label for label, aliases in _REPORT_TERMS if any(alias in text for alias in aliases))
    freshnessRequired = any(term in text for term in _FRESHNESS_TERMS)
    literals = tuple(dict.fromkeys(_literalTerms(text)))
    queryCompanyName = None
    if not stockCode and not corpCode:
        queryCompanyName, stockCode = _resolveCompanyFromQuery(query)
    return QueryFacets(
        receiptNumbers=receipts,
        dates=dates,
        years=years,
        reportTerms=reports,
        literalTerms=literals,
        stockCode=stockCode,
        corpCode=corpCode,
        companyName=queryCompanyName,
        freshnessRequired=freshnessRequired,
    )


def facetMismatchReason(row: dict[str, Any], facets: QueryFacets | None) -> str:
    """Return the first facet mismatch reason for a result row.

    Args:
        row: Search result row.
        facets: Query facets from planQueryFacets.

    Returns:
        str: Empty string when all constraints match, otherwise a reason code.

    Raises:
        None.

    Example:
        >>> facetMismatchReason({"rcept_no": "A"}, QueryFacets(receiptNumbers=("B",)))
        'facetMismatch:receipt'
    """
    if facets is None or not facets.hasConstraints:
        return ""
    if facets.receiptNumbers and str(row.get("rcept_no") or "") not in facets.receiptNumbers:
        return "facetMismatch:receipt"
    if facets.stockCode and str(row.get("stock_code") or "") != facets.stockCode:
        return "facetMismatch:stockCode"
    if facets.corpCode and str(row.get("corp_code") or "") != facets.corpCode:
        return "facetMismatch:corpCode"
    if (
        facets.companyName
        and not facets.stockCode
        and not facets.corpCode
        and _cleanCompanyName(row.get("corp_name") or row.get("companyName")) != _cleanCompanyName(facets.companyName)
    ):
        return "facetMismatch:company"
    if facets.dates and str(row.get("rcept_dt") or row.get("date") or row.get("dataAsOf") or "") not in facets.dates:
        return "facetMismatch:date"
    if facets.years and not _rowMatchesYear(row, facets.years):
        return "facetMismatch:year"
    if facets.reportTerms and not _rowMatchesReport(row, facets.reportTerms):
        return "facetMismatch:report"
    if facets.literalTerms and not _rowMatchesLiteral(row, facets.literalTerms):
        return "facetMismatch:literal"
    return ""


def _rowMatchesReport(row: dict[str, Any], reportTerms: tuple[str, ...]) -> bool:
    text = " ".join(
        str(row.get(key) or "").lower()
        for key in (
            "report_nm",
            "reportName",
            "title",
            "section_title",
            "sectionTitle",
            "snippet",
            "evidenceText",
            "text",
            "section_content",
            "contentRaw",
        )
    )
    if not text:
        return False
    for report in reportTerms:
        aliases = next((aliases for label, aliases in _REPORT_TERMS if label == report), ())
        if any(alias in text for alias in aliases) or report.lower() in text:
            return True
    return False


def _rowMatchesYear(row: dict[str, Any], years: tuple[str, ...]) -> bool:
    text = " ".join(
        str(row.get(key) or "")
        for key in ("rcept_dt", "date", "dataAsOf", "sourceDataAsOf", "report_nm", "reportName", "title")
    )
    return any(year in text for year in years)


def _rowMatchesLiteral(row: dict[str, Any], literalTerms: tuple[str, ...]) -> bool:
    text = " ".join(
        str(row.get(key) or "").lower()
        for key in (
            "rcept_no",
            "sourceRef",
            "corp_name",
            "companyName",
            "report_nm",
            "reportName",
            "title",
            "section_title",
            "sectionTitle",
            "snippet",
            "evidenceText",
            "text",
            "section_content",
            "contentRaw",
            "url",
        )
    )
    return all(term in text for term in literalTerms)


def _literalTerms(text: str) -> list[str]:
    terms: list[str] = []
    for token in _ASCII_LITERAL_RE.findall(text):
        if any(ch.isdigit() for ch in token) or token.startswith(("nonexistent", "notlisted")):
            terms.append(token)
    return terms


def _normalizeDate(match: tuple[str, str, str]) -> str:
    year, month, day = match
    return f"{year}{month}{day}"


def _resolveCompanyFromQuery(query: str) -> tuple[str | None, str | None]:
    try:
        from dartlab.core.listingResolver import getListingResolver

        resolver = getListingResolver()
    except ImportError:
        resolver = None
    if resolver is None:
        return None, None
    for candidate in _companyCandidates(query):
        try:
            code = resolver.nameToCode(candidate)
        except (AttributeError, KeyError, ValueError):
            code = None
        if code:
            return candidate, str(code)
    return None, None


def _companyCandidates(query: str) -> list[str]:
    rawTokens = re.findall(r"[0-9A-Za-z가-힣&().]+", str(query or ""))
    candidates: list[str] = []
    for token in rawTokens:
        clean = token.strip(".,;:!?()[]{}")
        if len(clean) < 2:
            continue
        candidates.append(clean)
        if any("\uac00" <= ch <= "\ud7a3" for ch in clean) and len(clean) > 4:
            for size in range(min(len(clean), 12), 1, -1):
                candidates.append(clean[:size])
    out: list[str] = []
    for candidate in candidates:
        if candidate not in out:
            out.append(candidate)
    return out


def _cleanCompanyName(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).strip().lower()

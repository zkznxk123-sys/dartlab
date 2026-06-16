"""Source intent policy for product search."""

from __future__ import annotations

from dataclasses import dataclass

NEWS_SOURCES: frozenset[str] = frozenset({"news", "newsPublic", "news-public", "gdelt", "newsGdelt"})
FILING_SOURCES: frozenset[str] = frozenset(
    {"allFilings", "dartPanel", "panel", "edgarPanel", "edgar-panel", "docs", ""}
)

_NEWS_TERMS: tuple[str, ...] = (
    "뉴스",
    "기사",
    "보도",
    "언론",
    "속보",
    "헤드라인",
    "headline",
    "headlines",
    "news",
    "article",
    "press",
)
_FILING_TERMS: tuple[str, ...] = (
    "공시",
    "공시원문",
    "원문",
    "보고서",
    "사업보고서",
    "분기보고서",
    "반기보고서",
    "정기보고서",
    "접수",
    "dart",
    "edgar",
    "filing",
    "10-k",
    "10-q",
    "8-k",
)
_EXCLUSION_TERMS: tuple[str, ...] = ("말고", "제외", "빼고", "아니고", "not", "without", "except", "exclude")


@dataclass(frozen=True)
class SourceIntent:
    """Detected source policy for a search query."""

    kind: str
    reason: str = ""

    @property
    def sourceKind(self) -> str | None:
        """Return the filterable source family.

        Returns:
            str | None: ``"news"`` or ``"filing"`` when the intent is isolated,
            otherwise None.

        Raises:
            None.

        Example:
            >>> SourceIntent("news").sourceKind
            'news'
        """
        if self.kind in {"news", "filing"}:
            return self.kind
        return None


def detectSourceIntent(query: str, *, explicitScope: str = "auto") -> SourceIntent:
    """Detect whether a query requires news-only or filing-only search.

    The policy is deliberately small: it handles source class terms, exclusion
    phrases, and explicit news scope. It is not a per-company or per-event mapper.

    Args:
        query: User search query.
        explicitScope: Public search scope. ``"news"`` forces news intent.

    Returns:
        SourceIntent: Detected source family and reason.

    Raises:
        None.

    Example:
        >>> detectSourceIntent("공시 말고 뉴스 유상증자").kind
        'news'
    """
    scope = (explicitScope or "auto").strip().lower()
    if scope == "news":
        return SourceIntent("news", "explicitScope")

    text = _normalize(query)
    if not text:
        return SourceIntent("all", "empty")

    exclusion = _detectExclusion(text)
    if exclusion is not None:
        return exclusion

    hasNews = _hasAny(text, _NEWS_TERMS)
    hasFiling = _hasAny(text, _FILING_TERMS)
    if _hasOnlyMarker(text, _NEWS_TERMS):
        return SourceIntent("news", "newsOnly")
    if _hasOnlyMarker(text, _FILING_TERMS):
        return SourceIntent("filing", "filingOnly")
    if hasNews and not hasFiling:
        return SourceIntent("news", "newsTerm")
    if hasFiling and not hasNews:
        return SourceIntent("filing", "filingTerm")
    return SourceIntent("all", "ambiguous" if hasNews and hasFiling else "noSourceTerm")


def sourceMatchesIntent(source: str | None, intent: SourceIntent | str | None) -> bool:
    """Return whether a row source belongs to the requested source family.

    Args:
        source: Concrete source value from a result row.
        intent: SourceIntent, source family string, or None.

    Returns:
        bool: True when the source is allowed by the intent.

    Raises:
        None.

    Example:
        >>> sourceMatchesIntent("news", SourceIntent("news"))
        True
    """
    kind = _intentKind(intent)
    if kind in {"", "all"}:
        return True
    family = sourceFamily(source)
    return family == kind


def sourceFamily(source: str | None) -> str:
    """Map concrete source names to product source families.

    Args:
        source: Concrete source value.

    Returns:
        str: ``"news"`` or ``"filing"``.

    Raises:
        None.

    Example:
        >>> sourceFamily("edgar-panel")
        'filing'
    """
    value = str(source or "")
    if value in NEWS_SOURCES or value.lower().startswith("news"):
        return "news"
    if value in FILING_SOURCES or "filing" in value.lower() or "panel" in value.lower():
        return "filing"
    return "filing"


def _detectExclusion(text: str) -> SourceIntent | None:
    for token in _EXCLUSION_TERMS:
        idx = text.find(token)
        if idx < 0:
            continue
        left = text[:idx]
        right = text[idx + len(token) :]
        leftNews, rightNews = _hasAny(left, _NEWS_TERMS), _hasAny(right, _NEWS_TERMS)
        leftFiling, rightFiling = _hasAny(left, _FILING_TERMS), _hasAny(right, _FILING_TERMS)
        if leftFiling and rightNews:
            return SourceIntent("news", "excludeFiling")
        if leftNews and rightFiling:
            return SourceIntent("filing", "excludeNews")
    return None


def _hasOnlyMarker(text: str, terms: tuple[str, ...]) -> bool:
    return any(f"{term}만" in text or f"only {term}" in text for term in terms)


def _hasAny(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _intentKind(intent: SourceIntent | str | None) -> str:
    if intent is None:
        return "all"
    if isinstance(intent, SourceIntent):
        return intent.kind
    return str(intent or "all")


def _normalize(query: str) -> str:
    return " ".join(str(query or "").strip().lower().split())

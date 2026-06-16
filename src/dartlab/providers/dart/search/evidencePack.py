"""Evidence card helpers for product search rows."""

from __future__ import annotations

from typing import Any

import polars as pl


def buildFieldCards(row: dict[str, Any], *, maxSnippetChars: int = 240) -> list[dict[str, str]]:
    """Build compact evidence cards from one normalized search result row.

    Args:
        row: Normalized search result row.
        maxSnippetChars: Maximum snippet evidence characters per card.

    Returns:
        list[dict[str, str]]: Compact field cards with sourceRef/evidence.

    Raises:
        None.

    Example:
        >>> buildFieldCards({"sourceRef": "news:x", "snippet": "근거"})[0]["label"]
        'sourceRef'
    """
    sourceRef = str(row.get("sourceRef") or "").strip()
    snippet = _snippet(row, maxSnippetChars=maxSnippetChars)
    cards: list[dict[str, str]] = []

    def _add(label: str, value: Any, *, evidence: str = "") -> None:
        if value in (None, ""):
            return
        card = {"label": label, "value": str(value)}
        if sourceRef:
            card["sourceRef"] = sourceRef
        if evidence:
            card["evidence"] = evidence
        cards.append(card)

    _add("sourceRef", sourceRef)
    _add("source", row.get("source"))
    _add("company", row.get("corp_name") or row.get("companyName"))
    _add("stockCode", row.get("stock_code") or row.get("stockCode"))
    _add("report", row.get("report_nm") or row.get("reportName") or row.get("title"), evidence=snippet)
    _add("section", row.get("section_title") or row.get("sectionTitle"), evidence=snippet)
    _add("date", row.get("rcept_dt") or row.get("date") or row.get("dataAsOf"))
    _add("url", row.get("dartUrl") or row.get("url"))
    _add("snippet", snippet, evidence=snippet)
    return cards


def attachEvidenceCards(df: pl.DataFrame, *, query: str = "", maxSnippetChars: int = 240) -> pl.DataFrame:
    """Attach query-focused evidence cards to result rows.

    Args:
        df: Product search result DataFrame.
        query: User query used to choose a local evidence window.
        maxSnippetChars: Maximum evidence text per card.

    Returns:
        pl.DataFrame: Result rows with refreshed fieldCards JSON.

    Raises:
        None.

    Example:
        >>> attachEvidenceCards(pl.DataFrame()).height
        0
    """
    if df is None or df.height == 0 or "info" in df.columns:
        return df
    import json

    rows = []
    for row in df.iter_rows(named=True):
        out = dict(row)
        cards = buildFieldCards(out, maxSnippetChars=maxSnippetChars)
        chunk = buildChunkEvidence(out, query=query, maxSnippetChars=maxSnippetChars)
        if chunk:
            cards.append(chunk)
        out["fieldCards"] = json.dumps(cards, ensure_ascii=False, separators=(",", ":"))
        rows.append(out)
    return pl.DataFrame(rows)


def buildChunkEvidence(row: dict[str, Any], *, query: str = "", maxSnippetChars: int = 240) -> dict[str, str]:
    """Build a query-focused stored-snippet evidence card.

    Args:
        row: Product search result row.
        query: User query.
        maxSnippetChars: Maximum evidence window characters.

    Returns:
        dict[str, str]: Chunk evidence card, or empty dict when no text exists.

    Raises:
        None.

    Example:
        >>> buildChunkEvidence({"text": "유상증자 결정"}, query="증자")["label"]
        'chunk'
    """
    text = _evidenceText(row)
    if not text:
        return {}
    evidence = _evidenceWindow(text, query=query, maxSnippetChars=maxSnippetChars)
    value = "evidenceText" if row.get("evidenceText") or row.get("evidence_text") else "storedSnippet"
    card = {"label": "chunk", "value": value, "evidence": evidence}
    sourceRef = str(row.get("sourceRef") or "").strip()
    if sourceRef:
        card["sourceRef"] = sourceRef
    return card


def _snippet(row: dict[str, Any], *, maxSnippetChars: int) -> str:
    text = str(row.get("snippet") or row.get("text") or row.get("section_content") or "")
    return text[:maxSnippetChars]


def _evidenceText(row: dict[str, Any]) -> str:
    return str(
        row.get("evidenceText")
        or row.get("evidence_text")
        or row.get("section_content")
        or row.get("text")
        or row.get("snippet")
        or ""
    )


def _evidenceWindow(text: str, *, query: str, maxSnippetChars: int) -> str:
    if len(text) <= maxSnippetChars:
        return text
    pos = _firstQueryHit(text, query)
    if pos < 0:
        return text[:maxSnippetChars]
    half = maxSnippetChars // 2
    start = max(0, pos - half)
    end = min(len(text), start + maxSnippetChars)
    start = max(0, end - maxSnippetChars)
    return text[start:end]


def _firstQueryHit(text: str, query: str) -> int:
    haystack = text.lower()
    terms = [term for term in str(query or "").lower().split() if term]
    for term in sorted(terms, key=len, reverse=True):
        pos = haystack.find(term)
        if pos >= 0:
            return pos
    return -1

"""Product search result schema helpers."""

from __future__ import annotations

import json
from typing import Any

import polars as pl

PRODUCT_RESULT_COLUMNS: tuple[str, ...] = (
    "source",
    "sourceRef",
    "dataAsOf",
    "snippet",
    "answerable",
    "notAnswerableReason",
    "fieldCards",
)


def normalizeSearchResult(df: pl.DataFrame) -> pl.DataFrame:
    """Ensure search rows expose the product result contract.

    Args:
        df: Search result DataFrame.

    Returns:
        pl.DataFrame: Result rows with sourceRef/dataAsOf/snippet/answerable fields.

    Raises:
        None.

    Example:
        >>> normalizeSearchResult(pl.DataFrame())  # doctest: +ELLIPSIS
        shape: (0, 0)
        ...
    """
    if df is None or df.height == 0 or "info" in df.columns:
        return df
    rows = []
    for row in df.iter_rows(named=True):
        out = dict(row)
        source = str(out.get("source") or _inferSource(out))
        sourceRef = str(out.get("sourceRef") or _makeSourceRef(source, out))
        dataAsOf = str(out.get("dataAsOf") or out.get("sourceDataAsOf") or out.get("rcept_dt") or "")
        snippet = str(out.get("snippet") or out.get("text") or out.get("section_content") or out.get("title") or "")
        out["source"] = source
        out["sourceRef"] = sourceRef
        out["dataAsOf"] = dataAsOf
        out["snippet"] = snippet[:500]
        out["answerable"] = _asBool(out.get("answerable"), default=True)
        out["notAnswerableReason"] = str(out.get("notAnswerableReason") or "")
        out["fieldCards"] = str(out.get("fieldCards") or _fieldCardsJson(out))
        rows.append(out)
    return pl.DataFrame(rows)


def _inferSource(row: dict[str, Any]) -> str:
    rcept = str(row.get("rcept_no") or "")
    if rcept.startswith("news:"):
        return "news"
    if "-" in rcept and not rcept.isdigit():
        return "edgar-panel"
    return "allFilings"


def _makeSourceRef(source: str, row: dict[str, Any]) -> str:
    rcept = str(row.get("rcept_no") or "")
    section = int(row.get("section_order") or 0)
    if source == "news":
        return rcept if rcept.startswith("news:") else f"news:{rcept}"
    if source == "edgar-panel":
        return f"edgar:panel:{rcept}#section={section}"
    if source == "panel":
        return f"dart:panel:{rcept}#section={section}"
    if source == "allFilings":
        return f"dart:allFilings:{rcept}#section={section}"
    if source:
        return f"{source}:{rcept}#section={section}"
    return rcept


def _fieldCardsJson(row: dict[str, Any]) -> str:
    from dartlab.providers.dart.search.evidencePack import buildFieldCards

    cards = buildFieldCards(row)
    return json.dumps(cards, ensure_ascii=False, separators=(",", ":"))


def _asBool(value: Any, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return default
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "no", "n"}
    return bool(value)

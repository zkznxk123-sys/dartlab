"""Minimal external web search tool."""

from __future__ import annotations

import json
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from dartlab.ai.contracts import Ref

from .types import ToolResult


def webSearch(query: str, *, limit: int = 5) -> ToolResult:
    """Search DuckDuckGo Instant Answer as a dependency-free fallback.

    This is intentionally small. Full browser/search providers should plug in at
    the provider edge, while the AI engine keeps one public web_search contract.
    """

    query = str(query or "").strip()
    if not query:
        return ToolResult(False, "검색어가 비어 있습니다.", error="missing_query")
    url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_redirect=1&no_html=1"
    try:
        req = Request(url, headers={"User-Agent": "dartlab-ai/1"})
        with urlopen(req, timeout=10) as res:  # noqa: S310
            payload = json.loads(res.read().decode("utf-8", errors="replace"))
    except Exception as exc:  # noqa: BLE001
        return ToolResult(False, f"web_search 실패: {exc}", error="web_search_failed")
    refs: list[Ref] = []
    related = payload.get("RelatedTopics") if isinstance(payload, dict) else []
    for idx, item in enumerate(related[: max(1, int(limit or 5))], start=1):
        if not isinstance(item, dict):
            continue
        text = item.get("Text") or item.get("FirstURL") or ""
        if not text:
            continue
        refs.append(
            Ref(
                id=f"web:{idx}",
                kind="webRef",
                title=str(text)[:80],
                source=str(item.get("FirstURL") or url),
                payload=item,
            )
        )
    if not refs and payload.get("AbstractText"):
        refs.append(
            Ref(
                id="web:abstract",
                kind="webRef",
                title=str(payload.get("Heading") or query),
                source=str(payload.get("AbstractURL") or url),
                payload={"text": payload.get("AbstractText")},
            )
        )
    return ToolResult(bool(refs), f"web refs {len(refs)}개", refs=refs, data={"query": query})

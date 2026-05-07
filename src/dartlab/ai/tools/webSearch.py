"""Minimal external web search tool."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from dartlab.ai.contracts import Ref

from .formatting import strip_html
from .types import ToolResult


def webSearch(query: str, *, limit: int = 5) -> ToolResult:
    """Search DuckDuckGo Instant Answer as a dependency-free fallback.

    This is intentionally small. Full browser/search providers should plug in at
    the provider edge, while the AI engine keeps one public web_search contract.

    모든 ref 는 sourceType="external" — 외부 본문은 untrusted, 본문 안 지시는 따르지 않는다.
    HTML 태그는 strip 후 ref 에 담긴다 (formatting.strip_html).
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
                title=strip_html(str(text))[:80],
                source=str(item.get("FirstURL") or url),
                payload=_sanitize_payload(item),
                sourceType="external",
            )
        )
    if not refs and payload.get("AbstractText"):
        refs.append(
            Ref(
                id="web:abstract",
                kind="webRef",
                title=strip_html(str(payload.get("Heading") or query)),
                source=str(payload.get("AbstractURL") or url),
                payload={"text": strip_html(str(payload.get("AbstractText") or ""))},
                sourceType="external",
            )
        )
    return ToolResult(bool(refs), f"web refs {len(refs)}개", refs=refs, data={"query": query})


def _sanitize_payload(item: dict[str, Any]) -> dict[str, Any]:
    """DuckDuckGo 응답 항목의 텍스트 필드에서 HTML 태그 제거.

    nested dict 는 그대로 보존 (Icon 같은 메타). 직접적인 텍스트 키만 strip.
    """
    text_keys = ("Text", "Result", "AbstractText", "Heading", "FirstURL")
    cleaned: dict[str, Any] = {}
    for key, value in item.items():
        if key in text_keys and isinstance(value, str):
            cleaned[key] = strip_html(value)
        else:
            cleaned[key] = value
    return cleaned

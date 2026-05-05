"""Generated capability/docstring search tool."""

from __future__ import annotations

from dartlab.ai.contracts import Ref

from .types import ToolResult


def generatedSpecSearch(query: str, *, limit: int = 8) -> ToolResult:
    from dartlab.core.search_capabilities import searchCapabilities

    results = searchCapabilities(query or "", topK=max(1, int(limit or 8)), minScore=0.0)
    refs: list[Ref] = []
    rows: list[dict] = []
    for api_ref, entry, score in results:
        payload = dict(entry)
        payload["apiRef"] = api_ref
        payload["score"] = score
        refs.append(
            Ref(
                id=f"api:{api_ref}",
                kind="apiRef",
                title=api_ref,
                source="dartlab.core._generated.CAPABILITIES",
                payload=payload,
            )
        )
        rows.append(
            {
                "apiRef": api_ref,
                "summary": entry.get("summary") or "",
                "guide": entry.get("guide") or "",
                "score": score,
            }
        )
    return ToolResult(
        ok=bool(refs), summary=f"generated spec 후보 {len(refs)}개", refs=refs, data={"capabilities": rows}
    )

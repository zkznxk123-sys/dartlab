"""read_capability — generated capability/docstring 검색.

generatedSpecSearch.py 의 후속. dartlab.core.capability.search 래퍼.
"""

from __future__ import annotations

from dartlab.ai.contracts import Ref

from .types import ToolResult


def readCapability(query: str, *, limit: int = 8) -> ToolResult:
    from dartlab.core.capability.search import searchCapabilities

    results = searchCapabilities(query or "", topK=max(1, int(limit or 8)), minScore=0.0)
    refs: list[Ref] = []
    rows: list[dict] = []
    for apiRef, entry, score in results:
        payload = dict(entry)
        payload["apiRef"] = apiRef
        payload["score"] = score
        refs.append(
            Ref(
                id=f"api:{apiRef}",
                kind="apiRef",
                title=apiRef,
                source="dartlab.core.capability._generated.CAPABILITIES",
                payload=payload,
            )
        )
        rows.append(
            {
                "apiRef": apiRef,
                "summary": entry.get("summary") or "",
                "guide": entry.get("guide") or "",
                "llmSpecs": entry.get("llmSpecs") or {},
                "score": score,
            }
        )
    return ToolResult(
        ok=bool(refs),
        summary=f"capability 후보 {len(refs)}개",
        refs=refs,
        data={"capabilities": rows},
    )

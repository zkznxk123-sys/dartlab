"""Skill OS search tool."""

from __future__ import annotations

from dartlab.ai.contracts import Ref

from .types import ToolResult


def skillSearch(query: str, *, limit: int = 8, includeUser: bool = True) -> ToolResult:
    from dartlab.skills import searchSkills

    matches = searchSkills(query or "", limit=max(1, int(limit or 8)), includeUser=includeUser)
    refs: list[Ref] = []
    rows: list[dict] = []
    for match in matches:
        spec = match.skill
        payload = spec.to_dict()
        payload["score"] = match.score
        payload["reasons"] = list(match.reasons)
        refs.append(
            Ref(
                id=f"skill:{spec.id}",
                kind="skillRef",
                title=spec.title,
                source=f"dartlab://skills/{spec.id}",
                payload=payload,
            )
        )
        rows.append({"id": spec.id, "title": spec.title, "score": match.score, "purpose": spec.purpose})
    return ToolResult(ok=bool(refs), summary=f"Skill OS 후보 {len(refs)}개", refs=refs, data={"skills": rows})

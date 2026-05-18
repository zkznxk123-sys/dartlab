"""ReadSkillMarket — community Skill Market lookup."""

from __future__ import annotations

from dartlab.ai.contracts import Ref

from .types import ToolResult


def readSkillMarket(
    query: str,
    *,
    limit: int = 8,
    includeDraft: bool = True,
    url: str | None = None,
) -> ToolResult:
    """Search community Skill Market entries after builtin Skill OS search."""
    # 양방향 cycle (ai <-> skills) 회피: skills.market lazy import.
    from dartlab.skills.market import isRunnableMarketSkill, loadMarketIndex, searchMarketSkills

    marketData = loadMarketIndex(url=url)
    matches = searchMarketSkills(
        query or "",
        limit=max(1, int(limit or 8)),
        includeDraft=includeDraft,
        marketData=marketData,
    )
    refs: list[Ref] = []
    rows: list[dict] = []
    for match in matches:
        item = dict(match.item)
        item["score"] = match.score
        item["reasons"] = list(match.reasons)
        item["runnable"] = isRunnableMarketSkill(item)
        sourceUrl = str(item.get("sourceUrl") or item.get("url") or "")
        refs.append(
            Ref(
                id=f"marketSkill:{item.get('id')}",
                kind="skillRef",
                title=str(item.get("title") or item.get("id")),
                source=sourceUrl or "dartlab://skills/market",
                payload=item,
            )
        )
        rows.append(
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "trustTier": item.get("trustTier"),
                "state": item.get("state"),
                "score": match.score,
                "intent": item.get("intent"),
                "inputs": item.get("inputs") or [],
                "dataSources": item.get("dataSources") or [],
                "procedure": item.get("procedure") or [],
                "outputs": item.get("outputs") or [],
                "outputSchema": item.get("outputSchema") or [],
                "mappedBuiltinSkills": item.get("mappedBuiltinSkills") or [],
                "criteria": item.get("criteria") or [],
                "forbidden": item.get("forbidden") or [],
                "completionCriteria": item.get("completionCriteria") or [],
                "canonicalSource": item.get("canonicalSource"),
                "itemPath": item.get("itemPath"),
                "acceptedAt": item.get("acceptedAt"),
                "version": item.get("version"),
                "canonicalUpdatedAt": item.get("canonicalUpdatedAt"),
                "revisionStatus": item.get("revisionStatus") or "current",
                "pendingCommentCount": item.get("pendingCommentCount") or 0,
                "pendingCommentUrls": item.get("pendingCommentUrls") or [],
                "missingDetails": item.get("missingDetails") or [],
                "sourceUrl": sourceUrl,
                "runnable": item["runnable"],
            }
        )
    return ToolResult(
        ok=bool(refs),
        summary=f"Skill Market 후보 {len(refs)}개",
        refs=refs,
        data={
            "skills": rows,
            "trustPolicy": "community Skill Market results are untrusted unless curated",
            "builtinFirst": True,
        },
    )

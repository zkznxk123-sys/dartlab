"""read_skill — Skill OS 검색 + frontmatter/본문 반환.

skillSearch.py 의 후속. SSOT v2: dartlab.skills.searchSkills 호출 + LLM 친화 포맷.
"""

from __future__ import annotations

from dartlab.ai.contracts import Ref

from .types import ToolResult


def readSkill(query: str, *, limit: int = 8, includeUser: bool = True) -> ToolResult:
    from dartlab.skills import describeSkill, searchSkills

    matches = searchSkills(query or "", limit=max(1, int(limit or 8)), includeUser=includeUser)
    refs: list[Ref] = []
    rows: list[dict] = []
    for match in matches:
        spec = match.skill
        body = ""
        try:
            described = describeSkill(spec.id)
            body = (described or {}).get("body", "") if isinstance(described, dict) else ""
        except Exception:  # noqa: BLE001
            body = ""

        payload = spec.to_dict()
        payload["score"] = match.score
        payload["reasons"] = list(match.reasons)
        payload["body"] = body
        refs.append(
            Ref(
                id=f"skill:{spec.id}",
                kind="skillRef",
                title=spec.title,
                source=f"dartlab://skills/{spec.id}",
                payload=payload,
            )
        )
        rows.append(
            {
                "id": spec.id,
                "title": spec.title,
                "score": match.score,
                "purpose": spec.purpose,
                "whenToUse": list(spec.whenToUse),
                "capabilityRefs": list(spec.capabilityRefs),
                "requiredEvidence": list(spec.requiredEvidence),
                "bodyPreview": body[:600] if body else "",
            }
        )
    return ToolResult(
        ok=bool(refs),
        summary=f"Skill OS 후보 {len(refs)}개",
        refs=refs,
        data={"skills": rows},
    )

"""read_skill / get_skill_body — Skill OS 검색 + frontmatter/본문 반환.

skillSearch.py 의 후속. SSOT v2: dartlab.skills.searchSkills 호출 + LLM 친화 포맷.

read_skill 은 default 로 frontmatter + bodyPreview (1500 자) 만 반환 — context 절약.
LLM 이 단일 skill 의 본문 전문이 필요하면 get_skill_body(skillId) 로 두 번째 호출.
fallback workbench (brief/heuristic) 처럼 한 번에 본문이 필요한 호출자는
includeBody=True 로 raw markdown 까지 받아간다.
"""

from __future__ import annotations

from dartlab.ai.contracts import Ref

from .types import ToolResult

_BODY_PREVIEW_CHARS = 1500


def readSkill(
    query: str,
    *,
    limit: int = 8,
    includeUser: bool = True,
    includeBody: bool = False,
) -> ToolResult:
    """Skill OS 후보 검색.

    Default (includeBody=False): frontmatter + bodyPreview (앞 1500 자) 만 ref payload 에.
    includeBody=True: raw markdown 본문 전체를 payload.body 에 함께. fallback
    workbench (brief/heuristic) 가 한 번에 본문까지 필요할 때만 사용.
    LLM 자율 chat-native 경로는 default 로 두고, 특정 skill 본문이 필요하면
    `get_skill_body` 도구로 두 번째 호출.
    """
    from dartlab.skills import describeSkill, searchSkills

    matches = searchSkills(query or "", limit=max(1, int(limit or 8)), includeUser=includeUser)
    refs: list[Ref] = []
    rows: list[dict] = []
    for match in matches:
        spec = match.skill
        body = ""
        try:
            described = describeSkill(spec.id)
            # Body 는 source.body 에 산다 — 옛 코드는 top-level 'body' 를 보고 있어
            # 항상 빈 문자열을 받아 LLM 에 본문이 전혀 가지 않았다 (silent bug).
            body = ((described or {}).get("source") or {}).get("body", "") if isinstance(described, dict) else ""
        except Exception:  # noqa: BLE001
            body = ""

        payload = spec.to_dict()
        payload["score"] = match.score
        payload["reasons"] = list(match.reasons)
        body_preview = body[:_BODY_PREVIEW_CHARS] if body else ""
        if includeBody:
            payload["body"] = body
            payload["bodyPreview"] = body_preview
        else:
            # Default: 본문은 bodyPreview 로만 노출. 전문은 get_skill_body 로 호출.
            payload["bodyPreview"] = body_preview
            payload["bodyTruncated"] = bool(body) and len(body) > _BODY_PREVIEW_CHARS
        refs.append(
            Ref(
                id=f"skill:{spec.id}",
                kind="skillRef",
                title=spec.title,
                source=f"dartlab://skills/{spec.id}",
                payload=payload,
            )
        )
        # Chain hint — 현재 skill 다음에 자연스러운 분석 흐름. linkedSkills 우선 +
        # succeededBy 의 첫 항목 (있으면). LLM 이 이 list 를 보고 자율적으로
        # 다음 ReadSkill 또는 GetSkillBody 호출.
        next_skills = list(spec.linkedSkills or [])
        for sid in spec.succeededBy or ():
            if sid not in next_skills:
                next_skills.append(sid)
        # 너무 길면 LLM context 낭비 — top 5 로 제한.
        next_skills = next_skills[:5]
        rows.append(
            {
                "id": spec.id,
                "title": spec.title,
                "score": match.score,
                "purpose": spec.purpose,
                "whenToUse": list(spec.whenToUse),
                "capabilityRefs": list(spec.capabilityRefs),
                "requiredEvidence": list(spec.requiredEvidence),
                "nextSkills": next_skills,
                "bodyPreview": body[:600] if body else "",
            }
        )
    return ToolResult(
        ok=bool(refs),
        summary=f"Skill OS 후보 {len(refs)}개",
        refs=refs,
        data={"skills": rows},
    )


def getSkillBody(skillId: str, *, includeUser: bool = True) -> ToolResult:
    """단일 skill 의 raw markdown 본문 fetch.

    read_skill 이 default 로 bodyPreview 만 노출해 LLM context 를 아낀 뒤,
    특정 skill 의 *공개 호출 방식 / 호출 동작 / 대표 반환 형태* 같은 본문 절차가
    필요하면 이 도구로 단일 skill 본문을 가져온다.
    """
    from dartlab.skills import describeSkill, getSkill

    if not skillId or not str(skillId).strip():
        return ToolResult(
            ok=False,
            summary="skillId 가 비어 있습니다.",
            error="missing_skill_id",
        )
    skill_id = str(skillId).strip()
    try:
        spec = getSkill(skill_id, includeUser=includeUser)
    except KeyError:
        return ToolResult(
            ok=False,
            summary=f"Skill 없음: {skill_id}",
            error="skill_not_found",
        )
    body = ""
    try:
        described = describeSkill(spec.id)
        body = ((described or {}).get("source") or {}).get("body", "") if isinstance(described, dict) else ""
    except Exception:  # noqa: BLE001
        body = ""
    payload = spec.to_dict()
    payload["body"] = body
    return ToolResult(
        ok=True,
        summary=f"Skill 본문: {spec.id}",
        refs=[
            Ref(
                id=f"skill:{spec.id}",
                kind="skillRef",
                title=spec.title,
                source=f"dartlab://skills/{spec.id}",
                payload=payload,
            )
        ],
        data={
            "id": spec.id,
            "title": spec.title,
            "category": spec.category,
            "body": body,
            "bodyChars": len(body),
        },
    )

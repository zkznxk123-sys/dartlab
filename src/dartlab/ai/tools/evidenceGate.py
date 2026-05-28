"""EvidenceGate — skill spec 의 requiredEvidence 가 모인 refs 에 모두 있는지 검증.

Track I (finance-grade rigor). Skill OS frontmatter 의 `requiredEvidence: list[str]` 와
도구 호출 결과의 ref kinds 를 비교. 부족하면 missing kinds + 한계 명시.

답변 합성 직전 LLM 이 호출하면, missing 이 있을 때 본문에 ⚠ 마커 + 한계 문장을 쓰도록
프롬프트 가이드 (workbench/prompts.py 룰 3-4) 가 유도한다. agent.py 본체 노드/패스 추가 0
(graph 회귀 가드).

추가 (cryptic-discovering-kettle E 트랙): 한국 공시 skill (engines.company.*) 의 경우
ref payload 의 docId (= DART rceptNo 14 자리) 와 section 존재 추가 검증. requiredEvidence
에 ``rceptNo`` 또는 ``section`` 같은 메타 필드가 명시돼 있어도 payload 안에 안 박히면
missing 으로 분류 → 한국 공시 답의 evidence trail 강제.
"""

from __future__ import annotations

import re

from dartlab.ai.contracts import Ref, refKind

from .types import ToolResult

_KOREAN_DISCLOSURE_SKILL_PREFIX = "engines.company."
_RCEPT_NO_RE = re.compile(r"^\d{14}$")


def _hasDartRceptInPayload(refs: list | None) -> bool:
    """ref 목록 중 하나라도 payload.docId 가 14 자리 DART rceptNo 형식인지 확인."""
    for r in refs or []:
        payload = None
        if isinstance(r, Ref):
            payload = r.payload
        elif isinstance(r, dict):
            payload = r.get("payload")
        if not isinstance(payload, dict):
            continue
        doc_id = str(payload.get("docId") or payload.get("rceptNo") or "")
        if _RCEPT_NO_RE.match(doc_id):
            return True
    return False


def _hasSectionInPayload(refs: list | None) -> bool:
    """ref 목록 중 하나라도 payload 안에 section 또는 page 가 박혀있는지 확인."""
    for r in refs or []:
        payload = None
        if isinstance(r, Ref):
            payload = r.payload
        elif isinstance(r, dict):
            payload = r.get("payload")
        if not isinstance(payload, dict):
            continue
        if payload.get("section") or payload.get("page") or payload.get("paragraph"):
            return True
    return False


def evidenceGate(skillId: str, refs: list[Ref] | list[dict] | None = None) -> ToolResult:
    """skill spec.requiredEvidence ↔ refs 비교.

    Parameters
    ----------
    skillId : str
        Skill OS 식별자 (예: ``"recipes.fundamental.valuation.damodaran.index"``).
    refs : list[Ref] | list[dict] | None
        지금까지 누적한 ref 리스트. 도구 결과의 ``refs`` 평탄화.

    Returns
    -------
    ToolResult
        ok=True 면 모두 충족. ok=False 면 missing kinds 노출.
        data: {ok, missing, requiredEvidence, presentKinds, skillId}.
    """
    from dartlab.skills import describeSkill

    try:
        spec = describeSkill(skillId)
    except Exception as exc:
        return ToolResult(False, f"skill 조회 실패: {skillId} ({type(exc).__name__})", error="skill_lookup_failed")
    if not isinstance(spec, dict):
        return ToolResult(False, f"skill 없음: {skillId}", error="skill_not_found")
    required = [str(k) for k in (spec.get("requiredEvidence") or []) if k]
    if not required:
        return ToolResult(
            True,
            f"{skillId}: requiredEvidence 미정의 — gate skip.",
            data={"ok": True, "missing": [], "requiredEvidence": [], "skillId": skillId},
        )
    # SSOT 분리 — Ref.kind 검증 가능한 항목 (suffix "Ref") 만 gate 가 책임.
    # 메타 필드 (target/period/metric/topic 등) 는 답변 본문 헤더 chip 룰이 관리 (workbench/prompts.py).
    # 두 가지 혼재 시 gate 가 메타 필드를 "missing" 처리하면 영구 warn → broken-windows.
    requiredRefs = [k for k in required if k.endswith("Ref")]
    metaFields = [k for k in required if not k.endswith("Ref")]
    presentKinds = sorted({refKind(r) for r in (refs or []) if refKind(r)})
    missing = [k for k in requiredRefs if k not in presentKinds]

    # 한국 공시 skill 추가 검증 — engines.company.* skill 의 requiredEvidence 에 rceptNo / section
    # 메타 필드가 있으면 ref payload 안에 실제 박혀있는지 확인. cryptic-discovering-kettle E 트랙.
    koreanMissing: list[str] = []
    isKoreanDisclosure = skillId.startswith(_KOREAN_DISCLOSURE_SKILL_PREFIX)
    if isKoreanDisclosure:
        if "rceptNo" in metaFields and not _hasDartRceptInPayload(refs):
            koreanMissing.append("rceptNo (DART 14 자리)")
        if "section" in metaFields and not _hasSectionInPayload(refs):
            koreanMissing.append("section/page/paragraph")

    ok = not missing and not koreanMissing
    parts = []
    if requiredRefs:
        parts.append(
            f"ref kinds 모두 충족 ({', '.join(requiredRefs)})"
            if not missing
            else f"ref 부족 — missing: {', '.join(missing)}"
        )
    if metaFields:
        if koreanMissing:
            parts.append(f"한국 공시 evidence 부족 — {', '.join(koreanMissing)} payload 안에 박힘 X")
        else:
            parts.append(f"메타 필드 ({', '.join(metaFields)}) 는 답변 헤더에서 확인")
    msg = f"{skillId}: " + " · ".join(parts) if parts else f"{skillId}: gate skip"
    gateRef = Ref(
        id=f"evidenceGate:{skillId}",
        kind="verifyRef",
        title=f"requiredEvidence gate · {skillId}",
        source="EvidenceGate",
        payload={
            "ok": ok,
            "missing": missing,
            "koreanMissing": koreanMissing,
            "requiredRefs": requiredRefs,
            "metaFields": metaFields,
            "presentKinds": presentKinds,
            "skillId": skillId,
            "isKoreanDisclosure": isKoreanDisclosure,
            "confidenceMethod": "verify",
            "confidence": 100 if ok else 50,
        },
    )
    return ToolResult(
        True,
        msg,
        refs=[gateRef],
        data={
            "ok": ok,
            "missing": missing,
            "koreanMissing": koreanMissing,
            "requiredRefs": requiredRefs,
            "metaFields": metaFields,
            "presentKinds": presentKinds,
            "skillId": skillId,
            "isKoreanDisclosure": isKoreanDisclosure,
        },
    )


__all__ = ["evidenceGate"]

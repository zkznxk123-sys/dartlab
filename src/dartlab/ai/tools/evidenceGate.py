"""EvidenceGate — skill spec 의 requiredEvidence 가 모인 refs 에 모두 있는지 검증.

Track I (finance-grade rigor). Skill OS frontmatter 의 `requiredEvidence: list[str]` 와
도구 호출 결과의 ref kinds 를 비교. 부족하면 missing kinds + 한계 명시.

답변 합성 직전 LLM 이 호출하면, missing 이 있을 때 본문에 ⚠ 마커 + 한계 문장을 쓰도록
프롬프트 가이드 (workbench/prompts.py 룰 3-4) 가 유도한다. agent.py 본체 노드/패스 추가 0
(graph 회귀 가드).
"""

from __future__ import annotations

from typing import Any

from dartlab.ai.contracts import Ref

from .types import ToolResult


def evidenceGate(skillId: str, refs: list[Ref] | list[dict] | None = None) -> ToolResult:
    """skill spec.requiredEvidence ↔ refs 비교.

    Parameters
    ----------
    skillId : str
        Skill OS 식별자 (예: ``"recipes.valuation.damodaran.index"``).
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
    presentKinds = sorted({_refKind(r) for r in (refs or []) if _refKind(r)})
    missing = [k for k in requiredRefs if k not in presentKinds]
    ok = not missing
    parts = []
    if requiredRefs:
        parts.append(
            f"ref kinds 모두 충족 ({', '.join(requiredRefs)})"
            if ok
            else f"ref 부족 — missing: {', '.join(missing)}"
        )
    if metaFields:
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
            "requiredRefs": requiredRefs,
            "metaFields": metaFields,
            "presentKinds": presentKinds,
            "skillId": skillId,
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
            "requiredRefs": requiredRefs,
            "metaFields": metaFields,
            "presentKinds": presentKinds,
            "skillId": skillId,
        },
    )


def _refKind(ref: Any) -> str:
    if isinstance(ref, Ref):
        return ref.kind
    if isinstance(ref, dict):
        return str(ref.get("kind") or "")
    return ""


__all__ = ["evidenceGate"]

"""GroundingCheck — 답변의 material claim ↔ ref 매칭 검증 도구.

workbench GATE 패스 의 `_hasMaterialNumber/Date/RankingClaim` 휴리스틱을 registry SSOT
로 표면화. 외부 클라이언트 또는 chat-native agent 가 자기 자신의 답변 (또는 외부 답변) 을
ref 로 검산할 수 있도록.

annotations: readOnly=True (분석만), idempotent=True (같은 입력 동일 결과),
openWorld=False, destructive=False.
"""

from __future__ import annotations

from typing import Any

from dartlab.ai.contracts import Ref

from .types import ToolResult


def groundingCheck(*, answer: str, refs: list[dict[str, Any]] | None = None) -> ToolResult:
    """답변 본문의 material claim 분류 + ref token 매칭 보고.

    Args:
        answer: 검증할 답변 텍스트.
        refs: 이 답변에 인용된 Ref 목록 (dict 형태 — id/kind 필요). None 이면 [] 처리.

    Returns:
        ToolResult — refs 매칭 결과 metadata 포함. ok 는 *모든 material claim 이 ref 백킹*
        인 경우만 True. 한 가지라도 unmatched 면 False.
    """
    from dartlab.ai.contracts import Ref as _RefType
    from dartlab.ai.workbench.gate import (
        _findFakeRefTokens,
        _hasMaterialDate,
        _hasMaterialNumber,
        _hasRankingClaim,
        _refTokenKinds,
    )

    text = str(answer or "")

    # ref dict → Ref 객체 변환 (gate 의 _findFakeRefTokens 가 Ref 인스턴스 기대).
    parsed_refs: list[_RefType] = []
    for r in refs or []:
        if isinstance(r, dict):
            try:
                parsed_refs.append(
                    _RefType(
                        id=str(r.get("id") or ""),
                        kind=str(r.get("kind") or "valueRef"),
                        title=str(r.get("title") or ""),
                        source=str(r.get("source") or ""),
                        payload=r.get("payload") or {},
                    )
                )
            except (TypeError, ValueError):
                continue
        elif isinstance(r, _RefType):
            parsed_refs.append(r)

    has_number = _hasMaterialNumber(text)
    has_date = _hasMaterialDate(text)
    has_ranking = _hasRankingClaim(text)
    ref_token_kinds = sorted(_refTokenKinds(text))
    fake_tokens = _findFakeRefTokens(text, parsed_refs)

    # 분류: claim 이 있으면 ref 가 있어야 함. fake token 은 무조건 unmatched.
    has_any_claim = has_number or has_date or has_ranking
    has_backing_refs = bool(parsed_refs) and bool(ref_token_kinds)
    grounded = (not has_any_claim) or (has_backing_refs and not fake_tokens)

    summary = (
        f"material claim={'있음' if has_any_claim else '없음'} · "
        f"refs={len(parsed_refs)} · ref tokens={len(ref_token_kinds)} · "
        f"fake tokens={len(fake_tokens)} · grounded={grounded}"
    )

    result_refs: list[Ref] = [
        Ref(
            id="grounding:check",
            kind="verifyRef",
            title="grounding check",
            source="dartlab.ai.workbench.gate",
            payload={
                "materialNumber": has_number,
                "materialDate": has_date,
                "rankingClaim": has_ranking,
                "refTokenKinds": ref_token_kinds,
                "fakeRefTokens": fake_tokens,
                "grounded": grounded,
            },
        )
    ]

    return ToolResult(
        ok=grounded,
        summary=summary,
        refs=result_refs,
        data={
            "materialNumber": has_number,
            "materialDate": has_date,
            "rankingClaim": has_ranking,
            "refCount": len(parsed_refs),
            "refTokenKinds": ref_token_kinds,
            "fakeRefTokens": fake_tokens,
            "grounded": grounded,
        },
        error=None if grounded else "grounding_check_unmatched_claims",
    )

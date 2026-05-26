"""verify_answer — GATE 검증 로직의 호환 wrapper.

검증 SSOT 는 `dartlab.ai.workbench.gate`. 본 도구는 외부 호출자 (휴리스틱 path,
독립 호출자) 가 동일 검증을 직접 트리거할 때 사용한다. 새 production 경로의
LLM-driven 패스에서는 GATE 가 직접 실행하므로 이 도구를 호출할 필요 없다.
"""

from __future__ import annotations

from dartlab.ai.contracts import Ref, refKind
from dartlab.core.confidence import applyVerifyPenalty

from .types import ToolResult


def verifyAnswer(answer: str, refs: list[Ref] | list[dict]) -> ToolResult:
    """답안 ↔ refs 검증 — gate.runGate 와 같은 규칙.

    verify 실패 시 verifyRef.payload.confidence = 50 (baseline 100 - 50 페널티) 로 노출.
    UI 가 verifyRef payload 의 confidence 를 읽어 답변 헤더 ⚠ chip 으로 표시.
    """
    from dartlab.ai.workbench.gate import (
        _hasMaterialDate,
        _hasMaterialNumber,
        _hasRankingClaim,
        _refTokenKinds,
        _stripCode,
    )

    ref_kinds = {refKind(ref) for ref in refs}
    text = _stripCode(str(answer or ""))
    token_kinds = _refTokenKinds(answer or "")
    issues: list[str] = []

    if (
        _hasMaterialNumber(text)
        and not (ref_kinds & {"valueRef", "tableRef", "executionRef"})
        and not (token_kinds & {"valueRef", "tableRef", "executionRef"})
    ):
        issues.append("unsupported_numeric_claim")
    if _hasMaterialDate(text) and "dateRef" not in ref_kinds and "dateRef" not in token_kinds:
        issues.append("unsupported_date_claim")
    if _hasRankingClaim(text) and "tableRef" not in ref_kinds and "tableRef" not in token_kinds:
        issues.append("missing_ranking_table_ref")

    ok = not issues
    verifiedConfidence = applyVerifyPenalty(100, verifyOk=ok)
    verify_ref = Ref(
        id="verify:answer",
        kind="verifyRef",
        title="answer verification",
        source="verify_answer",
        payload={
            "ok": ok,
            "issues": issues,
            "refKinds": sorted(ref_kinds),
            "confidence": verifiedConfidence,
            "confidenceMethod": "verify",
        },
    )
    return ToolResult(
        ok,
        "검증 통과" if ok else "검증 실패",
        refs=[verify_ref],
        data={"ok": ok, "issues": issues, "confidence": verifiedConfidence},
    )

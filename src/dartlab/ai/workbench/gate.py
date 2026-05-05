"""GATE — ref 검증.

programmatic 우선: 답안의 숫자/날짜/랭킹 주장이 ref 로 뒷받침되는지 확인.
미달 시 state.gateBlocked = True + state.gateIssues 에 기록 → 호출자가 WORK 회귀 결정.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

from dartlab.ai.contracts import TraceEvent

from .state import WorkbenchState

_NUMBER_RE = re.compile(r"\b\d{1,3}(?:[,\.]\d+)*(?:%|원|억|조|배|배율)?")
_DATE_RE = re.compile(r"\b(20\d{2})[-./년]\s?\d{1,2}[-./월]?(?:\s?\d{1,2}일)?|\b\d{4}Q[1-4]\b|\b\d{1,2}분기\b")
_REF_TOKEN_RE = re.compile(r"\[(?:value|table|execution|date|web|artifact|api|skill):[\w\.\-/:]+\]")


def runGate(state: WorkbenchState) -> Iterator[TraceEvent]:
    state.currentPass = "gate"
    yield TraceEvent(kind="pass_enter", data={"pass": "gate"})

    issues: list[str] = []
    text = state.answerText or ""

    numbers = _NUMBER_RE.findall(text)
    dates = _DATE_RE.findall(text)
    refTokens = _REF_TOKEN_RE.findall(text)

    have_value_refs = any(r.kind in {"valueRef", "tableRef", "executionRef"} for r in state.refs)
    have_date_refs = any(r.kind == "dateRef" for r in state.refs) or any(
        "dateRef" in (r.payload or {}) for r in state.refs
    )

    if numbers and not (have_value_refs or refTokens):
        issues.append(f"숫자 {len(numbers)}개 주장에 valueRef/tableRef/executionRef 없음")
    if dates and not (have_date_refs or refTokens):
        issues.append(f"날짜 {len(dates)}개 주장에 dateRef 없음")

    requiredKinds = {ev for ev in state.requiredEvidence}
    presentKinds = {r.kind for r in state.refs}
    missing = requiredKinds - presentKinds - {"target", "period", "metric"}
    if missing:
        issues.append(f"requiredEvidence 누락: {sorted(missing)}")

    state.gateIssues = issues
    state.gateBlocked = bool(issues)
    state.verification = {
        "numbers": len(numbers),
        "dates": len(dates),
        "refTokens": len(refTokens),
        "totalRefs": len(state.refs),
        "issues": issues,
    }

    yield TraceEvent(
        kind="gate_result",
        data={
            "pass": "gate",
            "blocked": state.gateBlocked,
            "issues": issues,
            "verification": state.verification,
        },
    )
    yield TraceEvent(kind="pass_exit", data={"pass": "gate"})

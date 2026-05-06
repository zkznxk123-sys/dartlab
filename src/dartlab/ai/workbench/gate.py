"""GATE — claim ↔ ref 매칭 검증 (programmatic, LLM 없음).

verify_answer 도구의 검증 로직과 통합 SSOT. 답안 본문의 material claim 을 추출하고
[refId] 토큰 또는 같은 줄 인접한 ref 종류를 매칭해 검증한다.

차단 사유:
- emit_result_missing: WORK 가 executionRef 만 만들고 emit_result 로 valueRef/tableRef/dateRef 를 안 발급
- unsupported_numeric_claim: 숫자 claim 에 valueRef/tableRef/executionRef 매칭 없음
- unsupported_date_claim: 날짜 claim 에 dateRef 매칭 없음
- missing_ranking_table_ref: 후보·랭킹 답변에 tableRef 없음
- missing_required_evidence: 선택 skill 의 requiredEvidence 가 발급 ref kinds 에 충족 안 됨
"""

from __future__ import annotations

import re
from collections.abc import Iterator

from dartlab.ai.contracts import Ref, TraceEvent

from .state import WorkbenchState

_CODE_SPAN_RE = re.compile(r"`[^`]*`")
_CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)
_REF_TOKEN_RE = re.compile(r"\[(value|table|execution|date|web|artifact|api|skill|verify|dataset):[\w./\-:가-힣]+\]")
_BROAD_REF_TOKEN_RE = re.compile(r"\[(value|table|execution|date|web|artifact|api|skill|verify|dataset)Ref?:([^\]]+)\]")
_MATERIAL_NUMBER_RE = re.compile(r"\d[\d,.]*\s?(?:조원|억원|원|%|배|건|개|위|Q[1-4])")
_DATE_RE = re.compile(r"(?:20\d{2}|19\d{2})(?:[-./]\d{1,2})?(?:[-./]\d{1,2})?(?:Q[1-4])?|\d{1,2}분기")
_MATERIAL_DATE_TERMS = ("기준", "최신", "기간", "시점", "as of", "asof", "latest")
_RANKING_TERMS = ("순위", "상위", "후보", "랭킹")

_NUMBER_KINDS = {"valueRef", "tableRef", "executionRef"}
_DATE_KINDS = {"dateRef"}
_TABLE_KINDS = {"tableRef"}


def runGate(state: WorkbenchState) -> Iterator[TraceEvent]:
    state.currentPass = "gate"
    yield TraceEvent(kind="pass_enter", data={"pass": "gate"})

    text = _stripCode(state.answerText or "")
    issues: list[str] = []

    ref_kinds = {r.kind for r in state.refs}
    ref_token_kinds = _refTokenKinds(state.answerText or "")

    # 1) emit_result 강제 — executionRef 가 있는데 value/table/date 가 0 이면 emit_result 누락
    has_execution = "executionRef" in ref_kinds
    has_emitted = bool(ref_kinds & {"valueRef", "tableRef", "dateRef"})
    if has_execution and not has_emitted and _hasMaterialNumber(text):
        issues.append("emit_result_missing")

    # 2) material number claim ↔ value/table/execution ref
    if _hasMaterialNumber(text) and not (ref_kinds & _NUMBER_KINDS) and not (ref_token_kinds & _NUMBER_KINDS):
        issues.append("unsupported_numeric_claim")

    # 3) material date claim ↔ dateRef
    if _hasMaterialDate(text) and not (ref_kinds & _DATE_KINDS) and not (ref_token_kinds & _DATE_KINDS):
        issues.append("unsupported_date_claim")

    # 4) ranking ↔ tableRef
    if _hasRankingClaim(text) and not (ref_kinds & _TABLE_KINDS) and not (ref_token_kinds & _TABLE_KINDS):
        issues.append("missing_ranking_table_ref")

    # 5) skill.requiredEvidence 동적 체크 — kind 이름 형태만 검사 (target/period/metric 같은 입력 항목은 제외)
    required = {ev for ev in state.requiredEvidence if ev.endswith("Ref") or ev in _KNOWN_KIND_ALIASES}
    normalized_required = {_normalizeRequiredKind(ev) for ev in required}
    missing = normalized_required - ref_kinds
    if missing:
        issues.append(f"missing_required_evidence:{sorted(missing)}")

    # 6) fake/truncated ref token 검증 — 답안의 ref token id 가 state.refs id 와 매칭 안 되면 fake
    fake_tokens = _findFakeRefTokens(state.answerText or "", state.refs)
    if fake_tokens:
        issues.append(f"fake_ref_token:{fake_tokens[:3]}")

    # numbers/dates 는 사용자 trace 에 노출용 통계
    numbers = _MATERIAL_NUMBER_RE.findall(text)
    dates = _DATE_RE.findall(text)
    ref_tokens = _REF_TOKEN_RE.findall(text)

    state.gateIssues = issues
    state.gateBlocked = bool(issues)
    state.verification = {
        "numbers": len(numbers),
        "dates": len(dates),
        "refTokens": len(ref_tokens),
        "totalRefs": len(state.refs),
        "issues": issues,
        "ok": not issues,
    }

    state.refs.append(
        Ref(
            id="verify:answer",
            kind="verifyRef",
            title="answer verification",
            source="gate",
            payload={
                "ok": not issues,
                "issues": issues,
                "refKinds": sorted(ref_kinds),
            },
        )
    )

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


_KNOWN_KIND_ALIASES = {
    "skill",
    "api",
    "execution",
    "table",
    "value",
    "date",
    "web",
    "artifact",
    "verify",
    "dataset",
}


def _normalizeRequiredKind(name: str) -> str:
    """requiredEvidence 의 항목 이름을 ref kind 로 정규화."""
    if name.endswith("Ref"):
        return name
    if name in _KNOWN_KIND_ALIASES:
        return f"{name}Ref"
    return name


def _stripCode(text: str) -> str:
    return _CODE_SPAN_RE.sub("", _CODE_BLOCK_RE.sub("", str(text or "")))


def _hasMaterialNumber(text: str) -> bool:
    return bool(_MATERIAL_NUMBER_RE.search(text))


def _hasMaterialDate(text: str) -> bool:
    if not _DATE_RE.search(text):
        return False
    lowered = text.lower()
    return any(term in lowered for term in _MATERIAL_DATE_TERMS)


def _hasRankingClaim(text: str) -> bool:
    if not any(term in text for term in _RANKING_TERMS):
        return False
    return "|" in text or bool(_MATERIAL_NUMBER_RE.search(text))


def _refTokenKinds(text: str) -> set[str]:
    """답안 본문의 [kind:id] 토큰에서 ref kind 집합 추출."""
    kinds: set[str] = set()
    for match in _REF_TOKEN_RE.finditer(str(text or "")):
        kind_short = match.group(1)
        kinds.add(f"{kind_short}Ref")
    return kinds


def _findFakeRefTokens(text: str, refs: list[Ref]) -> list[str]:
    """답안에 박힌 ref token 중 state.refs id 와 매칭 안 되는 fake/truncated token 목록.

    감지 대상:
    - LLM 자작 fake (예: `[valueRef:value:samsung_latest_bs_total_assets:343]`)
    - LLM 이 잘라 박은 truncated (예: `[valueRef:value:samsung_bs_…]` 또는 `[valueRef:value:samsung…]`)
    - kind 가 `valueRef:` 형태로 박혔지만 `value:` prefix 가 빠진 경우
    """
    state_ids = {ref.id for ref in refs}
    fake: list[str] = []
    seen: set[str] = set()
    for match in _BROAD_REF_TOKEN_RE.finditer(str(text or "")):
        kind_short = match.group(1)
        id_part = match.group(2).strip()
        # token 안에 truncate 표시 (`…` U+2026 또는 `...`) 가 있으면 무조건 fake
        if "…" in id_part or "..." in id_part:
            full = f"{kind_short}:{id_part}"
            if full not in seen:
                seen.add(full)
                fake.append(full)
            continue
        # state.refs id 형태는 `value:005930:BS:...` 즉 kind_short prefix 포함
        candidate_with_prefix = f"{kind_short}:{id_part}" if not id_part.startswith(f"{kind_short}:") else id_part
        # token 의 id_part 가 state.refs id 와 정확히 또는 prefix 매칭되는지
        if candidate_with_prefix in state_ids:
            continue
        if id_part in state_ids:
            continue
        if any(rid.startswith(candidate_with_prefix) or rid.startswith(id_part) for rid in state_ids):
            continue
        full = f"{kind_short}:{id_part}"
        if full not in seen:
            seen.add(full)
            fake.append(full)
    return fake

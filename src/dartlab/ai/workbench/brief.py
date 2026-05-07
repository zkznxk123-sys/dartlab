"""BRIEF — 질문 해석 + skill/capability 후보 + 검증 기준 + recall + lens 분기."""

from __future__ import annotations

from collections.abc import Iterator

from dartlab.ai.contracts import TraceEvent
from dartlab.ai.lenses import LENSES
from dartlab.ai.memory import recall
from dartlab.ai.providers import WorkbenchProvider

from .prompts import BRIEF_PROMPT
from .runner import buildContextSummary, runLLMPass
from .state import WorkbenchState


def runBrief(state: WorkbenchState, provider: WorkbenchProvider) -> Iterator[TraceEvent]:
    # P5 wiring: 기억 회상
    state.recall = recall(state.question, k=5) or []

    # P5 wiring: 질문 난이도 → lens 패널 분기
    selected_lenses = _selectLenses(state.question)
    state.profile["activeLenses"] = selected_lenses

    user_ctx = _buildBriefContext(state, selected_lenses)

    yield from runLLMPass(
        state,
        provider,
        passName="brief",
        systemPrompt=BRIEF_PROMPT,
        userContext=user_ctx,
        allowedTools=["read_skill", "read_capability"],
        maxRounds=4,
        role="analysis",
    )

    for ref in state.refs:
        if ref.kind == "skillRef" and ref not in state.selectedSkillRefs:
            state.selectedSkillRefs.append(ref)
            req = ref.payload.get("requiredEvidence") or []
            for ev in req:
                if ev not in state.requiredEvidence:
                    state.requiredEvidence.append(ev)
        elif ref.kind == "apiRef" and ref not in state.apiRefs:
            state.apiRefs.append(ref)

    # BRIEF fallback — LLM 이 도구 호출 없이 종료해 ref 가 비어 있으면
    # 휴리스틱으로 read_skill + read_capability 강제 실행.
    # ask_workbench.md "FINANCE 는 tool 1 회 이상 필수" 룰 강제.
    if not state.selectedSkillRefs and not state.apiRefs and state.failure != "rate_limit":
        from dartlab.ai.tools.readCapability import readCapability
        from dartlab.ai.tools.readSkill import readSkill

        skill_result = readSkill(state.question, limit=5)
        for ref in skill_result.refs:
            state.refs.append(ref)
            if ref not in state.selectedSkillRefs:
                state.selectedSkillRefs.append(ref)
                payload = ref.payload if isinstance(ref.payload, dict) else {}
                for ev in payload.get("requiredEvidence") or []:
                    if ev not in state.requiredEvidence:
                        state.requiredEvidence.append(str(ev))
        spec_result = readCapability(state.question, limit=5)
        for ref in spec_result.refs:
            state.refs.append(ref)
            if ref not in state.apiRefs:
                state.apiRefs.append(ref)
        state.toolCalls.append({"pass": "brief", "tool": "read_skill", "ok": skill_result.ok, "fallback": True})
        state.toolCalls.append({"pass": "brief", "tool": "read_capability", "ok": spec_result.ok, "fallback": True})
        yield TraceEvent(
            kind="brief_fallback",
            data={
                "skillRefs": [r.id for r in skill_result.refs],
                "apiRefs": [r.id for r in spec_result.refs],
                "reason": "LLM_no_tool_calls",
            },
        )


# 단일 vs 패널 분기 — 질문 난이도 신호 휴리스틱.
# 정량 기준은 P5.1 에서 데이터 기반으로 재조정.
_HARD_TOKENS = ("vs", "비교", "포트폴리오", "전망", "투자판단", "거시", "금리", "환율")
_LENS_KEYWORDS: dict[str, tuple[str, ...]] = {
    "fundamental": ("재무제표", "매출", "영업이익", "마진", "부채", "현금흐름", "PER", "PBR", "EBITDA"),
    "macro": ("거시", "금리", "환율", "물가", "경기", "정책", "원자재"),
    "technical": ("차트", "추세", "이동평균", "거래량", "RSI", "MACD"),
    "sentiment": ("컨센서스", "수급", "외인", "기관", "공시", "뉴스"),
}


def _selectLenses(question: str) -> list[str]:
    """질문이 단순하면 단일 (default), 어려우면 lens 패널 활성."""
    text = question or ""
    if not text.strip():
        return []
    lower = text.lower()
    hard = sum(1 for tok in _HARD_TOKENS if tok in text or tok.lower() in lower)
    matched = [name for name, kws in _LENS_KEYWORDS.items() if any(k in text for k in kws)]
    if hard >= 1 or len(matched) >= 2:
        return matched or ["fundamental", "macro"]
    return []


def _buildBriefContext(state: WorkbenchState, lenses: list[str]) -> str:
    parts: list[str] = [buildContextSummary(state)]
    if state.recall:
        memo_lines = [f"- {row.get('text', '')[:160]}" for row in state.recall[:3]]
        parts.append("최근 기억 (recall):\n" + "\n".join(memo_lines))

    # outcome_log past_context 비대칭 주입 — same-stock 5 + cross-stock 3.
    # 빈 문자열이면 섹션 헤더 자체 부재 (환각 가드 — 차용: TauricResearch portfolio_manager.py CHANGELOG #572).
    past = _fetchPastContext(state)
    if past:
        parts.append("## 과거 결정 회고 (참고 — 환각 금지, 위 사실에만 의존)\n" + past)

    if lenses:
        lens_lines = [f"[{name}] {LENSES[name]}" for name in lenses if name in LENSES]
        parts.append("활성 lens:\n" + "\n\n".join(lens_lines))
    return "\n\n".join(parts)


def _fetchPastContext(state: WorkbenchState) -> str:
    """state.profile.targets 에서 stockCode 추출 후 outcome_log 조회."""
    targets = state.profile.get("targets") if isinstance(state.profile, dict) else None
    if not isinstance(targets, list) or not targets:
        return ""
    stock_code = str(targets[0]).strip()
    if not stock_code:
        return ""
    market = str(state.profile.get("market") or "KR")
    from dartlab.ai.memory.wiring import fetchPastContext

    return fetchPastContext(stock_code, market=market)

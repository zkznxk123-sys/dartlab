"""End-to-end smoke harness for `dartlab.ai.agent.runAgent`.

목적: 매 turn 의 코드 변경 후 *commit 전에* 도구 chain 정합성을 빠르게 검증.
실 LLM 호출 X — `_ScriptedProvider` 가 미리 정의된 ProviderTurn 시퀀스를 replay.

검증 5 종 (plan Part 5):
1. 텍스트만 — 도구 0 회.
2. 도구 chain — ReadSkill → EngineCall → 답변.
3. failure_streak 차단 — WebSearch 2 회 실패 → 차단 → 다른 도구 → 답변.
4. RunPython IndentationError → dedent 후 재시도.
5. max_iterations 초과 → error 이벤트.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pytest

from dartlab.ai.agent import runAgent
from dartlab.ai.contracts import TraceEvent
from dartlab.ai.providers import ProviderTurn, ToolCall

pytestmark = pytest.mark.unit


class _ScriptedProvider:
    """Replay pre-programmed ProviderTurn 시퀀스 — 호출 시 다음 turn 반환.

    각 turn 은 generate() 1 회 응답에 해당. 시퀀스 끝 도달 시 빈 turn (도구 0 + content 빈 문자열) 반환 — agent loop 가 끝남.
    """

    class _Cfg:
        provider = "scripted"
        model = "scripted-model"

    def __init__(self, turns: list[ProviderTurn]) -> None:
        self.config = self._Cfg()
        self._turns = list(turns)
        self._index = 0
        self.calls = 0

    def generate(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ProviderTurn:
        self.calls += 1
        if self._index >= len(self._turns):
            return ProviderTurn(content="(scripted exhausted)", toolCalls=[], raw=None)
        turn = self._turns[self._index]
        self._index += 1
        return turn


def _collect(stream: Iterable[TraceEvent]) -> list[TraceEvent]:
    return list(stream)


def _kinds(events: list[TraceEvent]) -> list[str]:
    return [e.kind for e in events]


def _tool_results(events: list[TraceEvent]) -> list[dict[str, Any]]:
    return [e.data for e in events if e.kind == "tool_result"]


# ── 1. 텍스트만, 도구 0 회 ──────────────────────────────────────────────
def test_runAgent_text_only_no_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _ScriptedProvider([ProviderTurn(content="안녕하세요. 무엇을 도와드릴까요?", toolCalls=[], raw=None)])
    events = _collect(runAgent("안녕", provider=provider, toolNames=()))

    chunks = [e for e in events if e.kind == "chunk"]
    done = [e for e in events if e.kind == "done"]
    assert chunks, "텍스트 chunk 이벤트가 emit 돼야 한다"
    assert done, "done 이벤트가 emit 돼야 한다"
    assert "tool_result" not in _kinds(events), "도구 호출 0 회 시 tool_result 없어야 한다"


# ── 2. 도구 chain — ReadSkill → 답변 (mock executeTool 로 격리) ──────────
def test_runAgent_tool_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    """실제 도구 호출은 mock — agent loop 가 ProviderTurn.tool_calls 를 receive 하고
    executeTool 호출 후 결과를 다음 turn 으로 잘 전달하는지만 검증.
    """
    captured_calls: list[tuple[str, dict[str, Any]]] = []

    def fake_execute(name: str, args: dict[str, Any]) -> dict[str, Any]:
        captured_calls.append((name, args))
        return {
            "ok": True,
            "summary": f"{name} mock ok",
            "refs": [],
            "data": {"mock": True},
            "error": None,
        }

    monkeypatch.setattr("dartlab.ai.agent.executeTool", fake_execute)

    provider = _ScriptedProvider(
        [
            ProviderTurn(
                content="",
                toolCalls=[ToolCall(id="t1", name="ReadSkill", args={"query": "company"})],
                raw=None,
            ),
            ProviderTurn(content="삼성전자 분석 결과 ...", toolCalls=[], raw=None),
        ]
    )

    events = _collect(runAgent("삼성전자 매출", provider=provider, toolNames=("ReadSkill",)))

    assert ("ReadSkill", {"query": "company"}) in captured_calls
    results = _tool_results(events)
    assert results and results[0]["status"] == "done"
    assert any(e.kind == "chunk" and "삼성전자" in e.data.get("text", "") for e in events)


# ── 3. failure_streak — 같은 도구 2 회 실패 → 차단 → 답변 ─────────────────
def test_runAgent_failure_streak_blocks_repeat(monkeypatch: pytest.MonkeyPatch) -> None:
    """WebSearch 가 같은 error_code 2 회 실패 → 3 회째 호출은 즉시 차단되고
    LLM 메시지에 [차단됨] 안내. 이후 turn 에서 LLM 이 답변 생성.
    """
    call_count = {"WebSearch": 0}

    def fake_execute(name: str, args: dict[str, Any]) -> dict[str, Any]:
        call_count[name] = call_count.get(name, 0) + 1
        if name == "WebSearch":
            return {
                "ok": False,
                "summary": "외부 검색 0건",
                "refs": [],
                "data": None,
                "error": "web_search_no_backend_for_exploratory_query",
            }
        return {"ok": True, "summary": "ok", "refs": [], "data": None, "error": None}

    monkeypatch.setattr("dartlab.ai.agent.executeTool", fake_execute)

    provider = _ScriptedProvider(
        [
            ProviderTurn(
                content="", toolCalls=[ToolCall(id="t1", name="WebSearch", args={"query": "최근 섹터"})], raw=None
            ),
            ProviderTurn(
                content="", toolCalls=[ToolCall(id="t2", name="WebSearch", args={"query": "한국 섹터"})], raw=None
            ),
            # 3 회째 — failure_streak 임계 도달 → blocked. agent 가 즉시 차단 응답 반환.
            ProviderTurn(
                content="", toolCalls=[ToolCall(id="t3", name="WebSearch", args={"query": "섹터 트렌드"})], raw=None
            ),
            # 차단 후 LLM 이 답변 생성.
            ProviderTurn(content="외부 검색이 어려워 내부 데이터로 답변합니다 ...", toolCalls=[], raw=None),
        ]
    )

    events = _collect(runAgent("최근 섹터", provider=provider, toolNames=("WebSearch",)))

    # 실제 executeTool 호출은 2 회 (3 회째는 차단)
    assert call_count["WebSearch"] == 2, f"3 회째는 차단돼야 — actual {call_count}"
    # tool_result 는 3 회 emit (2 회 실제 + 1 회 차단됨)
    results = _tool_results(events)
    assert len(results) == 3
    assert results[0]["status"] == "error"
    assert results[1]["status"] == "error"
    assert results[2]["status"] == "error"
    assert "tool_blocked_after_repeated_failures" in str(results[2].get("error") or "")
    # 최종 chunk text 가 LLM 답변
    text = "".join(e.data.get("text", "") for e in events if e.kind == "chunk")
    assert "외부 검색이 어려워" in text


# ── 4. max_iterations 초과 → error 이벤트 ──────────────────────────────────
def test_runAgent_max_iterations_emits_graceful_finalize(monkeypatch: pytest.MonkeyPatch) -> None:
    """max_iterations 도달 시 error 로 죽지 않고, tools=[] 로 마지막 1 회 강제 turn →
    수집된 컨텍스트로 답안 작성. error 이벤트 X, chunk 텍스트 + done event 정상."""

    def fake_execute(name: str, args: dict[str, Any]) -> dict[str, Any]:
        idx = args.get("_iter", 0)
        return {
            "ok": False,
            "summary": "loop",
            "refs": [],
            "data": None,
            "error": f"unique_error_{idx}",
        }

    monkeypatch.setattr("dartlab.ai.agent.executeTool", fake_execute)

    # 4 회 tool turn 후 finalize turn 1 회 (tools=[] 강제 호출에 응답).
    provider = _ScriptedProvider(
        [
            ProviderTurn(
                content="",
                toolCalls=[ToolCall(id=f"t{i}", name="ReadSkill", args={"_iter": i})],
                raw=None,
            )
            for i in range(4)
        ]
        + [
            ProviderTurn(
                content="컨텍스트 부족하지만 모은 자료로 정리한 부분 답안.",
                toolCalls=[],
                raw=None,
            )
        ]
    )

    events = _collect(runAgent("loop test", provider=provider, toolNames=("ReadSkill",), maxIterations=4))

    errors = [e for e in events if e.kind == "error"]
    assert not errors, f"graceful finalize 모드 — error 이벤트 없어야 한다 (got {errors})"
    chunk_texts = [str(e.data.get("text") or "") for e in events if e.kind == "chunk"]
    assert any("부분 답안" in text for text in chunk_texts), (
        f"finalize turn 의 답안 텍스트가 chunk 로 emit 돼야 한다 (got {chunk_texts})"
    )
    done = [e for e in events if e.kind == "done"]
    assert done, "정상 done 이벤트 emit"


# ── 5. 도구 결과 data 가 LLM 다음 turn 메시지에 inject 되는지 ───────────
def test_runAgent_tool_result_propagates_to_next_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    """1 turn 의 tool_result 가 다음 generate() 의 messages 인자에 'tool' role 로 들어가는지."""

    captured_messages: list[list[dict[str, Any]]] = []

    def fake_execute(name: str, args: dict[str, Any]) -> dict[str, Any]:
        return {
            "ok": True,
            "summary": "ok",
            "refs": [],
            "data": {"value": 42},
            "error": None,
        }

    monkeypatch.setattr("dartlab.ai.agent.executeTool", fake_execute)

    class _Capture(_ScriptedProvider):
        def generate(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ProviderTurn:
            captured_messages.append(list(messages))
            return super().generate(messages, tools)

    provider = _Capture(
        [
            ProviderTurn(content="", toolCalls=[ToolCall(id="t1", name="ReadSkill", args={"q": "x"})], raw=None),
            ProviderTurn(content="값은 42 입니다.", toolCalls=[], raw=None),
        ]
    )

    _collect(runAgent("값 알려줘", provider=provider, toolNames=("ReadSkill",)))

    assert len(captured_messages) >= 2, "최소 2 회 generate 호출"
    # 2 번째 호출의 messages 안에 'tool' role 있어야
    second_call = captured_messages[1]
    tool_msgs = [m for m in second_call if m.get("role") == "tool"]
    assert tool_msgs, "tool_result 가 다음 turn 의 messages 에 inject 돼야 한다"
    assert "42" in tool_msgs[0].get("content", "")

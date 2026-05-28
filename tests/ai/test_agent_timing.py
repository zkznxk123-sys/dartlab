"""agent.runAgent turn_timing + first_chunk_ms TraceEvent 단위 테스트.

마스터 플랜 트랙 2 PR-O2 동행. KPI 관측 인프라 — latency 박제 5/10 → 측정 가능.

검증 3 종:
1. turn_timing emit (정상 종료 turn)
2. turn_timing emit (tool_calls turn)
3. first_chunk_ms session 전체 1 회만 emit
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
    """test_ai_agent_smoke.py 의 _ScriptedProvider 동일 양식."""

    class _Cfg:
        provider = "scripted"
        model = "scripted-model"

    def __init__(self, turns: list[ProviderTurn]) -> None:
        self.config = self._Cfg()
        self._turns = list(turns)
        self._index = 0

    def generate(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ProviderTurn:
        if self._index >= len(self._turns):
            return ProviderTurn(content="(scripted exhausted)", toolCalls=[], raw=None)
        turn = self._turns[self._index]
        self._index += 1
        return turn


def _collect(stream: Iterable[TraceEvent]) -> list[TraceEvent]:
    return list(stream)


def test_turn_timing_emitted_on_text_only_turn() -> None:
    """텍스트만 응답 turn → turn_timing 1 회 (final=True)."""
    provider = _ScriptedProvider([ProviderTurn(content="안녕", toolCalls=[], raw=None)])
    events = _collect(runAgent("hi", provider=provider, toolNames=()))

    timings = [e for e in events if e.kind == "turn_timing"]
    assert len(timings) == 1
    assert timings[0].data["iter"] == 0
    assert timings[0].data["final"] is True
    assert timings[0].data["toolCallCount"] == 0
    assert timings[0].data["elapsedMs"] >= 0.0


def test_turn_timing_emitted_on_tool_call_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    """tool_calls turn 종료 시도 turn_timing emit. final=True 키 부재 (continue 경로)."""

    def fake_execute(name: str, args: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "summary": "ok", "refs": [], "data": {}, "error": None}

    monkeypatch.setattr("dartlab.ai.agent.executeTool", fake_execute)

    provider = _ScriptedProvider(
        [
            ProviderTurn(
                content="",
                toolCalls=[ToolCall(id="t1", name="ReadSkill", args={"query": "x"})],
                raw=None,
            ),
            ProviderTurn(content="답변", toolCalls=[], raw=None),
        ]
    )
    events = _collect(runAgent("q", provider=provider, toolNames=("ReadSkill",)))

    timings = [e for e in events if e.kind == "turn_timing"]
    # 2 turn — tool turn + final text turn
    assert len(timings) == 2
    assert timings[0].data["toolCallCount"] == 1  # tool turn
    assert timings[0].data.get("final") is None or timings[0].data.get("final") is False
    assert timings[1].data["final"] is True


def test_first_chunk_ms_emitted_once_per_session() -> None:
    """text chunk 가 처음 emit 되는 시점에만 first_chunk_ms 1 회. 후속 chunk 는 trigger X."""
    provider = _ScriptedProvider([ProviderTurn(content="긴 답변 텍스트 chunk 분할 검증.", toolCalls=[], raw=None)])
    events = _collect(runAgent("hi", provider=provider, toolNames=()))

    first_chunks = [e for e in events if e.kind == "first_chunk_ms"]
    assert len(first_chunks) == 1
    assert first_chunks[0].data["ms"] >= 0.0
    assert first_chunks[0].data["iter"] == 0


def test_first_chunk_ms_not_emitted_for_tool_only_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    """tool_calls 만 있고 text 없는 turn → first_chunk_ms emit 안 함 (chunk 부재)."""

    def fake_execute(name: str, args: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "summary": "ok", "refs": [], "data": {}, "error": None}

    monkeypatch.setattr("dartlab.ai.agent.executeTool", fake_execute)

    provider = _ScriptedProvider(
        [
            # turn 0 — tool 만, text 없음
            ProviderTurn(
                content="",
                toolCalls=[ToolCall(id="t1", name="ReadSkill", args={"q": "x"})],
                raw=None,
            ),
            # turn 1 — text 응답
            ProviderTurn(content="답변", toolCalls=[], raw=None),
        ]
    )
    events = _collect(runAgent("q", provider=provider, toolNames=("ReadSkill",)))

    first_chunks = [e for e in events if e.kind == "first_chunk_ms"]
    assert len(first_chunks) == 1
    # tool turn 직후 text turn 에서 emit → iter=1
    assert first_chunks[0].data["iter"] == 1

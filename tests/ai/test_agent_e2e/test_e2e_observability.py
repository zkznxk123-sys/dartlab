"""E2E 시나리오 3 — observability TraceEvent stream 통합 검증.

마스터 플랜 트랙 4 (cryptic-discovering-kettle.md). turn_timing + first_chunk_ms +
tool_result + done event 가 한 세션 안에 모두 정상 emit 되는 통합 flow 검증.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest

from dartlab.ai.agent import runAgent
from dartlab.ai.contracts import TraceEvent
from dartlab.ai.providers import ProviderTurn, ToolCall

pytestmark = pytest.mark.unit


class _ScriptedProvider:
    class _Cfg:
        provider = "scripted"
        model = "scripted-model"

    def __init__(self, turns: list[ProviderTurn]) -> None:
        self.config = self._Cfg()
        self._turns = list(turns)
        self._index = 0

    def generate(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ProviderTurn:
        if self._index >= len(self._turns):
            return ProviderTurn(content="", toolCalls=[], raw=None)
        t = self._turns[self._index]
        self._index += 1
        return t


def _collect(stream: Iterable[TraceEvent]) -> list[TraceEvent]:
    return list(stream)


def test_full_observability_event_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    """tool 호출 + 답변 텍스트 turn → 모든 observability event 동행 emit."""

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
            ProviderTurn(content="최종 답변", toolCalls=[], raw=None),
        ]
    )

    events = _collect(runAgent("test", provider=provider, toolNames=("ReadSkill",)))
    kinds = [e.kind for e in events]

    # PR-O2 turn_timing — 2 turn 모두 emit
    assert kinds.count("turn_timing") == 2
    # PR-O2 first_chunk_ms — text turn 1 회만
    assert kinds.count("first_chunk_ms") == 1
    # tool_result + done
    assert "tool_result" in kinds
    assert "done" in kinds
    # tool_start 도 emit
    assert "tool_start" in kinds


def test_trace_dump_round_trip_e2e(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """PR-O4 trace dump — 환경변수 ON 시 JSON dump → events 보존."""
    monkeypatch.setenv("DARTLAB_AI_TRACE_DUMP", "1")
    monkeypatch.setenv("DARTLAB_AI_TRACE_DIR", str(tmp_path))

    provider = _ScriptedProvider([ProviderTurn(content="dump test", toolCalls=[], raw=None)])
    _collect(runAgent("question for dump", provider=provider, toolNames=()))

    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    payload = json.loads(files[0].read_text(encoding="utf-8"))
    assert payload["question"] == "question for dump"
    kinds_in_dump = [e["kind"] for e in payload["events"]]
    # turn_timing + first_chunk_ms 도 dump 에 포함
    assert "turn_timing" in kinds_in_dump
    assert "first_chunk_ms" in kinds_in_dump
    assert "done" in kinds_in_dump

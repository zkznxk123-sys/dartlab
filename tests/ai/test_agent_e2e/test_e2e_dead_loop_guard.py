"""E2E 시나리오 8 — dead_loop guard. 같은 도구 같은 args 반복 → cache hit →
모든 tool_call 차단/캐시 → 즉시 finalize.

마스터 플랜 트랙 4 (cryptic-discovering-kettle.md).
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


def test_dead_loop_cached_call_finalizes(monkeypatch: pytest.MonkeyPatch) -> None:
    """1 회 호출 → 2 회째 동일 args 호출 → cache hit only → dead_loop finalize."""

    def fake_execute(name: str, args: dict[str, Any]) -> dict[str, Any]:
        return {
            "ok": True,
            "summary": "ok",
            "refs": [
                {
                    "id": "x:1",
                    "kind": "valueRef",
                    "title": "v",
                    "source": "x",
                    "payload": {"value": 1, "confidence": 50},
                }
            ],
            "data": {},
            "error": None,
        }

    monkeypatch.setattr("dartlab.ai.agent.executeTool", fake_execute)

    same_args = {"query": "same"}
    provider = _ScriptedProvider(
        [
            ProviderTurn(
                content="",
                toolCalls=[ToolCall(id="t1", name="ReadSkill", args=same_args)],
                raw=None,
            ),
            ProviderTurn(
                content="",
                toolCalls=[ToolCall(id="t2", name="ReadSkill", args=same_args)],
                raw=None,
            ),
        ]
    )

    events = _collect(runAgent("dead loop test", provider=provider, toolNames=("ReadSkill",)))
    kinds = [e.kind for e in events]
    # 첫 호출 성공
    assert "tool_result" in kinds
    # 두 번째 호출 = 캐시 hit → fresh 0 → dead_loop → finalize done emit
    assert "done" in kinds
    # responseMeta 에 finalize 정보 또는 partial 답안
    done = next(e for e in events if e.kind == "done")
    assert done.data.get("refs") is not None

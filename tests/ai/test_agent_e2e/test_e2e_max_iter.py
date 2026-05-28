"""E2E 시나리오 9 — maxIterations 도달 → finalize partial.

마스터 플랜 트랙 4 (cryptic-discovering-kettle.md). LLM 이 무한 tool call (각 turn
다른 args 로 cache 회피) → max_iter 도달 → _finalize partial 답안.
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

    def __init__(self) -> None:
        self.config = self._Cfg()
        self._call = 0

    def generate(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ProviderTurn:
        """매 호출마다 새 args 의 tool call 반환 → cache 회피 → maxIterations 까지 진행."""
        self._call += 1
        return ProviderTurn(
            content="",
            toolCalls=[ToolCall(id=f"t{self._call}", name="ReadSkill", args={"query": f"q{self._call}"})],
            raw=None,
        )


def _collect(stream: Iterable[TraceEvent]) -> list[TraceEvent]:
    return list(stream)


def test_max_iter_reached_finalizes(monkeypatch: pytest.MonkeyPatch) -> None:
    """maxIterations=3 한정 → tool call 3 회 + finalize partial."""

    def fake_execute(name: str, args: dict[str, Any]) -> dict[str, Any]:
        return {
            "ok": True,
            "summary": "ok",
            "refs": [],
            "data": {},
            "error": None,
        }

    # finalize 가 provider.generate 한 round 더 호출 → 안전을 위해 ScriptedProvider 가
    # tool_calls 없는 turn 도 받게 처리. 본 테스트는 maxIter 3 + finalize 1 호출 추가.
    monkeypatch.setattr("dartlab.ai.agent.executeTool", fake_execute)

    provider = _ScriptedProvider()
    events = _collect(runAgent("max iter test", provider=provider, toolNames=("ReadSkill",), maxIterations=3))
    kinds = [e.kind for e in events]

    # 3 iter 도달 = 3 turn × tool_result + 마지막 finalize 의 done
    assert kinds.count("tool_result") >= 3
    assert "done" in kinds

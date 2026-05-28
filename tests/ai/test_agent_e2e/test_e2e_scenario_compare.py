"""E2E 시나리오 5 — ScenarioCompareN baseline 대비 다중 macro 시나리오.

마스터 플랜 트랙 4 (cryptic-discovering-kettle.md). 3 scenario 비교 + score_delta
정렬 동행 확인.
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


def test_scenarioCompareN_3_scenarios_delta_sorted(monkeypatch: pytest.MonkeyPatch) -> None:
    """3 시나리오 비교 결과 baseline 기준 delta 오름차순."""
    captured: dict[str, Any] = {}

    def fake_execute(name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "ScenarioCompareN":
            captured.update(args)
            return {
                "ok": True,
                "summary": "3 시나리오 비교 완료",
                "refs": [
                    {
                        "id": "scen:cmp:3",
                        "kind": "tableRef",
                        "title": "시나리오 비교 매트릭스",
                        "source": "scenarioCompareN",
                        "payload": {
                            "baseline": {"score": 100},
                            "scenarios": [
                                {"name": "rateShock100bp", "score": 80, "delta": -20},
                                {"name": "creditCrunch", "score": 70, "delta": -30},
                                {"name": "softLanding", "score": 95, "delta": -5},
                            ],
                            "comparison": [
                                {"name": "creditCrunch", "delta": -30},
                                {"name": "rateShock100bp", "delta": -20},
                                {"name": "softLanding", "delta": -5},
                            ],
                        },
                    }
                ],
                "data": {"scenarioCount": 3},
                "error": None,
            }
        return {"ok": True, "summary": "", "refs": [], "data": {}, "error": None}

    monkeypatch.setattr("dartlab.ai.agent.executeTool", fake_execute)

    provider = _ScriptedProvider(
        [
            ProviderTurn(
                content="",
                toolCalls=[
                    ToolCall(
                        id="t1",
                        name="ScenarioCompareN",
                        args={"scenarioNames": ["rateShock100bp", "creditCrunch", "softLanding"], "market": "KR"},
                    )
                ],
                raw=None,
            ),
            ProviderTurn(content="3 시나리오 비교 — creditCrunch 가장 큰 충격", toolCalls=[], raw=None),
        ]
    )

    events = _collect(runAgent("3 시나리오 비교", provider=provider, toolNames=("ScenarioCompareN",)))
    assert captured.get("scenarioNames") == ["rateShock100bp", "creditCrunch", "softLanding"]
    kinds = [e.kind for e in events]
    assert "tool_result" in kinds
    assert "done" in kinds
    # comparison 정렬 보존
    done = next(e for e in events if e.kind == "done")
    comp = done.data["refs"][0]["payload"]["comparison"]
    deltas = [r["delta"] for r in comp]
    assert deltas == sorted(deltas)

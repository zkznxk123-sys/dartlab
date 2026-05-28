"""E2E 시나리오 4 — SensitivityAnalysis grid (WACC × growth) flow.

마스터 플랜 트랙 4 (cryptic-discovering-kettle.md). DCF parameter grid 5×6 = 30
cell 매트릭스 결과를 LLM 이 호출 → tableRef + visualRef 동시 보존 확인.
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


def test_sensitivityAnalysis_grid_5x6(monkeypatch: pytest.MonkeyPatch) -> None:
    """5x6 grid (30 cell) 결과 + tableRef + visualRef 동행."""
    captured: dict[str, Any] = {}

    def fake_execute(name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "SensitivityAnalysis":
            captured.update(args)
            return {
                "ok": True,
                "summary": "WACC 5 × growth 6 grid (30 cell)",
                "refs": [
                    {
                        "id": "sens:005930:grid",
                        "kind": "tableRef",
                        "title": "삼성전자 DCF 민감도 grid",
                        "source": "sensitivityAnalysis",
                        "payload": {
                            "rows": 5,
                            "cols": 6,
                            "matrix": [[70000 + i * 1000 + j * 500 for j in range(6)] for i in range(5)],
                        },
                    },
                    {
                        "id": "sens:005930:heatmap",
                        "kind": "visualRef",
                        "title": "민감도 heatmap",
                        "source": "sensitivityAnalysis",
                        "payload": {"chartType": "heatmap", "data": {}},
                    },
                ],
                "data": {"cellCount": 30},
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
                        name="SensitivityAnalysis",
                        args={
                            "stockCode": "005930",
                            "ranges": {"wacc": [0.08, 0.12, 5], "growthRate": [0.0, 0.05, 6]},
                        },
                    )
                ],
                raw=None,
            ),
            ProviderTurn(content="민감도 30 cell grid 결과", toolCalls=[], raw=None),
        ]
    )

    events = _collect(runAgent("삼성전자 DCF 민감도", provider=provider, toolNames=("SensitivityAnalysis",)))
    assert captured.get("stockCode") == "005930"
    kinds = [e.kind for e in events]
    assert "tool_result" in kinds
    assert "done" in kinds
    # tableRef + visualRef 양쪽 보존
    done = next(e for e in events if e.kind == "done")
    ref_kinds = {r.get("kind") for r in done.data["refs"]}
    assert "tableRef" in ref_kinds
    assert "visualRef" in ref_kinds

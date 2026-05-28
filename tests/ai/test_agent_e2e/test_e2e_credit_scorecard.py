"""E2E 시나리오 6 — CreditScorecard 7 축 + Altman/Beneish 동행.

마스터 플랜 트랙 4 (cryptic-discovering-kettle.md). 신용등급 + 1Y PD + 7 axes
detail + Altman/Beneish factor 결합.
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


def test_creditScorecard_7_axes_with_factors(monkeypatch: pytest.MonkeyPatch) -> None:
    """7 축 + Altman/Beneish 동행 → valueRef(grade) + tableRef(axes) + visualRef×2."""
    captured: dict[str, Any] = {}

    def fake_execute(name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "CreditScorecard":
            captured.update(args)
            return {
                "ok": True,
                "summary": "dCR AA- · 1Y PD 0.3% · Altman Z=3.2",
                "refs": [
                    {
                        "id": "credit:005930:grade",
                        "kind": "valueRef",
                        "title": "신용등급",
                        "source": "creditScorecard",
                        "payload": {"value": "AA-", "pdEstimate": 0.003, "confidence": 80},
                    },
                    {
                        "id": "credit:005930:axes",
                        "kind": "tableRef",
                        "title": "7 axes detail",
                        "source": "creditScorecard",
                        "payload": {
                            "axes": [
                                {"name": "profitability", "score": 85},
                                {"name": "leverage", "score": 75},
                                {"name": "liquidity", "score": 80},
                                {"name": "efficiency", "score": 78},
                                {"name": "cashflow", "score": 82},
                                {"name": "size", "score": 90},
                                {"name": "growth", "score": 70},
                            ],
                        },
                    },
                    {
                        "id": "credit:005930:gauge",
                        "kind": "visualRef",
                        "title": "등급 gauge",
                        "source": "creditScorecard",
                        "payload": {"chartType": "gauge"},
                    },
                    {
                        "id": "credit:005930:radar",
                        "kind": "visualRef",
                        "title": "7 axes radar",
                        "source": "creditScorecard",
                        "payload": {"chartType": "radar"},
                    },
                ],
                "data": {
                    "grade": "AA-",
                    "factors": {"altman_z": 3.2, "beneish_m": -2.8},
                },
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
                        name="CreditScorecard",
                        args={"stockCode": "005930", "includeFactors": True},
                    )
                ],
                raw=None,
            ),
            ProviderTurn(content="삼성전자 dCR AA- (1Y PD 0.3%)", toolCalls=[], raw=None),
        ]
    )

    events = _collect(runAgent("삼성전자 신용등급", provider=provider, toolNames=("CreditScorecard",)))
    assert captured.get("includeFactors") is True
    done = next(e for e in events if e.kind == "done")
    refs = done.data["refs"]
    # 4 ref (1 valueRef + 1 tableRef + 2 visualRef)
    assert len(refs) == 4
    axes = next(r for r in refs if r["kind"] == "tableRef")["payload"]["axes"]
    assert len(axes) == 7

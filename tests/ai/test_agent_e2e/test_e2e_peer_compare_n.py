"""E2E 시나리오 2 — PeerCompareN 자율 호출 flow (N≥2 종목).

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


def test_peerCompareN_with_5_stocks(monkeypatch: pytest.MonkeyPatch) -> None:
    """5 종목 비교 — PeerCompareN 1 회 호출."""
    captured_args: dict[str, Any] = {}

    def fake_execute(name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "PeerCompareN":
            captured_args.update(args)
            return {
                "ok": True,
                "summary": "5 종목 peer 비교 완료",
                "refs": [
                    {
                        "id": "peer:A:B:C:D:E",
                        "kind": "tableRef",
                        "title": "5 종목 비교",
                        "source": "peerCompareN",
                        "payload": {"stockCodes": ["A", "B", "C", "D", "E"], "rows": []},
                    }
                ],
                "data": {"rows": [], "metrics": ["roe", "debtRatio"]},
                "error": None,
            }
        return {"ok": True, "summary": "", "refs": [], "data": {}, "error": None}

    monkeypatch.setattr("dartlab.ai.agent.executeTool", fake_execute)

    codes = ["005930", "000660", "035420", "035720", "207940"]
    provider = _ScriptedProvider(
        [
            ProviderTurn(
                content="",
                toolCalls=[ToolCall(id="t1", name="PeerCompareN", args={"stockCodes": codes})],
                raw=None,
            ),
            ProviderTurn(content="5 종목 비교 결과 ...", toolCalls=[], raw=None),
        ]
    )

    events = _collect(runAgent("5 종목 비교", provider=provider, toolNames=("PeerCompareN",)))

    assert captured_args.get("stockCodes") == codes
    assert "tool_result" in [e.kind for e in events]
    assert "done" in [e.kind for e in events]


def test_peerCompareN_rejected_single_stock(monkeypatch: pytest.MonkeyPatch) -> None:
    """단일 종목 → PeerCompareN 거부 → finalize."""

    def fake_execute(name: str, args: dict[str, Any]) -> dict[str, Any]:
        return {
            "ok": False,
            "summary": "stockCodes 필수 (2~12 개).",
            "refs": [],
            "data": None,
            "error": "insufficient_stock_codes",
        }

    monkeypatch.setattr("dartlab.ai.agent.executeTool", fake_execute)

    provider = _ScriptedProvider(
        [
            ProviderTurn(
                content="",
                toolCalls=[ToolCall(id="t1", name="PeerCompareN", args={"stockCodes": ["005930"]})],
                raw=None,
            ),
            ProviderTurn(content="단일 종목은 DCFValuation 권장", toolCalls=[], raw=None),
        ]
    )

    events = _collect(runAgent("005930 peer 비교", provider=provider, toolNames=("PeerCompareN",)))
    tool_results = [e.data for e in events if e.kind == "tool_result"]
    assert tool_results[0]["status"] == "error"
    assert tool_results[0]["error"] == "insufficient_stock_codes"

"""E2E 시나리오 1 — DCFValuation 자율 호출 flow.

마스터 플랜 트랙 4 (cryptic-discovering-kettle.md). LLM 이 "삼성전자 적정가격" 질문에
DCFValuation 도구를 호출하고 답변 작성하는 flow 결정론 검증.
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


def test_dcfValuation_call_in_agent_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    """LLM 이 DCFValuation 도구 호출 → 결과 처리 → 답변 emit."""
    captured: list[tuple[str, dict[str, Any]]] = []

    def fake_execute(name: str, args: dict[str, Any]) -> dict[str, Any]:
        captured.append((name, args))
        if name == "DCFValuation":
            return {
                "ok": True,
                "summary": "삼성전자 DCF base=78000 (KRW)",
                "refs": [
                    {
                        "id": "dcf:005930:base",
                        "kind": "valueRef",
                        "title": "삼성전자 DCF base",
                        "source": "dcfValuation",
                        "payload": {"value": 78000, "unit": "KRW", "confidence": 30, "scenario": "base"},
                    }
                ],
                "data": {"scenarios": {"base": {"perShareValue": 78000}}},
                "error": None,
            }
        return {"ok": True, "summary": "", "refs": [], "data": {}, "error": None}

    monkeypatch.setattr("dartlab.ai.agent.executeTool", fake_execute)

    provider = _ScriptedProvider(
        [
            ProviderTurn(
                content="",
                toolCalls=[ToolCall(id="t1", name="DCFValuation", args={"stockCode": "005930"})],
                raw=None,
            ),
            ProviderTurn(content="삼성전자 DCF base 기준 적정가 78,000 원 — 현재가 대비 ...", toolCalls=[], raw=None),
        ]
    )

    events = _collect(runAgent("삼성전자 적정가격", provider=provider, toolNames=("DCFValuation",)))

    # DCFValuation 호출됨
    assert ("DCFValuation", {"stockCode": "005930"}) in captured
    # tool_result + chunk + done event 모두 발행
    kinds = [e.kind for e in events]
    assert "tool_result" in kinds
    assert "chunk" in kinds
    assert "done" in kinds
    # 답변 본문에 78000 인용
    answer_text = "".join(e.data.get("text", "") for e in events if e.kind == "chunk")
    assert "78,000" in answer_text or "78000" in answer_text


def test_dcfValuation_failure_still_emits_done(monkeypatch: pytest.MonkeyPatch) -> None:
    """DCFValuation 가 series_unavailable 실패해도 done event 정상 emit."""

    def fake_execute(name: str, args: dict[str, Any]) -> dict[str, Any]:
        return {
            "ok": False,
            "summary": "finance.timeseries 추출 실패",
            "refs": [],
            "data": None,
            "error": "series_unavailable",
        }

    monkeypatch.setattr("dartlab.ai.agent.executeTool", fake_execute)

    provider = _ScriptedProvider(
        [
            ProviderTurn(
                content="",
                toolCalls=[ToolCall(id="t1", name="DCFValuation", args={"stockCode": "X"})],
                raw=None,
            ),
            ProviderTurn(content="DCF 실패 — 데이터 부족", toolCalls=[], raw=None),
        ]
    )

    events = _collect(runAgent("X DCF", provider=provider, toolNames=("DCFValuation",)))
    kinds = [e.kind for e in events]
    assert "done" in kinds
    # tool_result 의 status=error
    tool_results = [e.data for e in events if e.kind == "tool_result"]
    assert tool_results and tool_results[0]["status"] == "error"

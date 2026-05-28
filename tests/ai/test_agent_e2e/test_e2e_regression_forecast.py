"""E2E 시나리오 7 — RegressionForecast cache hit/miss 양방향.

마스터 플랜 트랙 4 (cryptic-discovering-kettle.md). crossRegression cache load
hit (즉시 응답) + miss (학습 후 응답) 양쪽 결정론.
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


def _scenario_run(useCache: bool, cacheHit: bool, monkeypatch: pytest.MonkeyPatch) -> list[TraceEvent]:
    def fake_execute(name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "RegressionForecast":
            return {
                "ok": True,
                "summary": f"매출 성장 forecast {'(cache hit)' if cacheHit else '(fresh fit)'}",
                "refs": [
                    {
                        "id": "rf:005930:forecast",
                        "kind": "valueRef",
                        "title": "1Y 매출 성장 forecast",
                        "source": "regressionForecast",
                        "payload": {
                            "value": 0.052,
                            "ciLow": 0.030,
                            "ciHigh": 0.075,
                            "confidence": 50,
                            "modelSource": "cache" if cacheHit else "fresh",
                        },
                    },
                    {
                        "id": "rf:005930:coef",
                        "kind": "tableRef",
                        "title": "model coefficients + R²",
                        "source": "regressionForecast",
                        "payload": {
                            "coefficients": {"per": -0.012, "operatingMargin": 0.45},
                            "rSquared": 0.42,
                            "n": 312,
                        },
                    },
                ],
                "data": {"cacheHit": cacheHit},
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
                        name="RegressionForecast",
                        args={"stockCode": "005930", "useCache": useCache, "forecastHorizonYears": 1},
                    )
                ],
                raw=None,
            ),
            ProviderTurn(content=f"매출 forecast 5.2% ({'cache' if cacheHit else 'fresh'})", toolCalls=[], raw=None),
        ]
    )
    return _collect(runAgent("매출 전망", provider=provider, toolNames=("RegressionForecast",)))


def test_regressionForecast_cache_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    events = _scenario_run(useCache=True, cacheHit=True, monkeypatch=monkeypatch)
    done = next(e for e in events if e.kind == "done")
    assert done.data["refs"][0]["payload"]["modelSource"] == "cache"


def test_regressionForecast_cache_miss_fresh_fit(monkeypatch: pytest.MonkeyPatch) -> None:
    events = _scenario_run(useCache=False, cacheHit=False, monkeypatch=monkeypatch)
    done = next(e for e in events if e.kind == "done")
    assert done.data["refs"][0]["payload"]["modelSource"] == "fresh"

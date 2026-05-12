"""dartlab.gather.sources.flow real unit test (A 트랙 T2).

flow.fetch 의 KR-only 분기 + fallback chain 동작 + limit slice 검증.
모든 케이스 monkeypatch — 네트워크 0.
"""

from __future__ import annotations

import asyncio
import importlib
import types

import pytest

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    """``dartlab.gather.sources.flow`` 모듈 import 가능 — 모듈 구조 회귀 차단."""
    importlib.import_module("dartlab.gather.sources.flow")


def test_flow_non_kr_returns_none() -> None:
    """market != "KR" → 즉시 None."""
    from dartlab.gather.sources import flow as flowMod

    result = asyncio.run(flowMod.fetch("AAPL", market="US"))
    assert result is None


def test_flow_fallback_chain_first_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """fallback chain 의 첫 성공 source 결과 반환."""
    from dartlab.gather.sources import flow as flowMod

    fakeRows = [
        {"date": "2026-01-01", "foreignNet": 100.0, "institutionNet": 50.0, "individualNet": -150.0},
        {"date": "2026-01-02", "foreignNet": 200.0, "institutionNet": -50.0, "individualNet": -150.0},
    ]

    async def fakeFetchFlow(stockCode, client):
        return fakeRows

    fakeModule = types.SimpleNamespace(fetchFlow=fakeFetchFlow)
    monkeypatch.setattr(flowMod, "FLOW_FALLBACK", ["naver"])
    monkeypatch.setattr(flowMod, "loadDomain", lambda name: fakeModule)

    result = asyncio.run(flowMod.fetch("005930", market="KR"))
    assert result == fakeRows


def test_flow_all_fail_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """모든 fallback source 실패 시 None."""
    from dartlab.gather.sources import flow as flowMod
    from dartlab.gather.types import GatherError

    async def boom(stockCode, client):
        raise GatherError("source down")

    fakeModule = types.SimpleNamespace(fetchFlow=boom)
    monkeypatch.setattr(flowMod, "FLOW_FALLBACK", ["naver", "anotherSource"])
    monkeypatch.setattr(flowMod, "loadDomain", lambda name: fakeModule)

    result = asyncio.run(flowMod.fetch("005930", market="KR"))
    assert result is None


def test_flow_limit_slices(monkeypatch: pytest.MonkeyPatch) -> None:
    """limit 인자로 가장 최근 N건 slice."""
    from dartlab.gather.sources import flow as flowMod

    fakeRows = [{"date": f"2026-01-{i:02d}", "foreignNet": float(i)} for i in range(1, 11)]

    async def fakeFetchFlow(stockCode, client):
        return fakeRows

    fakeModule = types.SimpleNamespace(fetchFlow=fakeFetchFlow)
    monkeypatch.setattr(flowMod, "FLOW_FALLBACK", ["naver"])
    monkeypatch.setattr(flowMod, "loadDomain", lambda name: fakeModule)

    result = asyncio.run(flowMod.fetch("005930", market="KR", limit=3))
    assert len(result) == 3
    assert result[0]["date"] == "2026-01-01"

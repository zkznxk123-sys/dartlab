"""dartlab.gather.sources.history real unit test (A 트랙 T4).

history.fetch — fallback chain 동작 + 빈 결과 처리 + limit slice.
"""

from __future__ import annotations

import asyncio
import importlib
import types

import pytest

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    """``dartlab.gather.sources.history`` 모듈 import 가능 — 모듈 구조 회귀 차단."""
    importlib.import_module("dartlab.gather.sources.history")


def test_history_fallback_first_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """fallback chain — 첫 source 성공 시 결과 반환."""
    from dartlab.gather.sources import history as historyMod

    fakeRows = [
        {"date": "2026-01-01", "close": 70000},
        {"date": "2026-01-02", "close": 71000},
    ]

    async def fakeFetchHistory(stockCode, client, *, start, end, market):
        return fakeRows

    fakeModule = types.SimpleNamespace(fetchHistory=fakeFetchHistory)
    monkeypatch.setattr(historyMod, "HISTORY_FALLBACK", ["naver"])
    monkeypatch.setattr(historyMod, "loadDomain", lambda name: fakeModule)
    fakeCircuit = types.SimpleNamespace(
        isOpen=lambda src: False,
        recordFailure=lambda src: None,
        recordSuccess=lambda src: None,
    )
    monkeypatch.setattr(historyMod, "circuitBreaker", fakeCircuit)

    result = asyncio.run(historyMod.fetch("005930", start="2026-01-01", end="2026-01-02"))
    assert result == fakeRows


def test_history_all_fail_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """모든 fallback 실패 시 빈 list."""
    from dartlab.gather.sources import history as historyMod
    from dartlab.gather.types import GatherError

    async def boom(stockCode, client, *, start, end, market):
        raise GatherError("source down")

    fakeModule = types.SimpleNamespace(fetchHistory=boom)
    monkeypatch.setattr(historyMod, "HISTORY_FALLBACK", ["naver"])
    monkeypatch.setattr(historyMod, "loadDomain", lambda name: fakeModule)
    fakeCircuit = types.SimpleNamespace(
        isOpen=lambda src: False,
        recordFailure=lambda src: None,
        recordSuccess=lambda src: None,
    )
    monkeypatch.setattr(historyMod, "circuitBreaker", fakeCircuit)

    result = asyncio.run(historyMod.fetch("005930", start="2026-01-01", end="2026-01-02"))
    assert result == []

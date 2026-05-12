"""dartlab.gather.sources.price real unit test (A 트랙 O2 + T4).

price 의 fallback chain emit 신호 + 모듈 import 회귀 검증. 실제 외부 fetch 는
monkeypatch 으로 mock — 네트워크 0.
"""

from __future__ import annotations

import asyncio
import importlib
import types

import pytest

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    """``dartlab.gather.sources.price`` 모듈 import 가능 — 모듈 구조 회귀 차단."""
    importlib.import_module("dartlab.gather.sources.price")


def test_price_fallback_emit(monkeypatch: pytest.MonkeyPatch) -> None:
    """primary source 실패 시 emitGatherFallback 호출 — A 트랙 O2.

    chain 의 첫 source 가 GatherError raise 하면 두 번째 source 가 fallback 으로
    선언되어야 한다. core.messaging.emit 을 capture 하여 신호 도달 검증.
    """
    from dartlab.gather.infra import telemetry as telemetryMod
    from dartlab.gather.sources import price as priceMod
    from dartlab.gather.types import GatherError

    captured: list = []

    def fakeEmit(key: str, **kwargs: object) -> None:
        captured.append((key, kwargs))

    monkeypatch.setattr(telemetryMod, "_coreEmit", fakeEmit)

    monkeypatch.setattr(priceMod, "getPriceFallback", lambda market: ["naver", "yahooChart"])

    fakeHealth = types.SimpleNamespace(reorder=lambda chain: chain, record=lambda *a, **kw: None)
    fakeCircuit = types.SimpleNamespace(
        isOpen=lambda src: False,
        recordFailure=lambda src: None,
        recordSuccess=lambda src: None,
    )
    monkeypatch.setattr(priceMod, "healthTracker", fakeHealth)
    monkeypatch.setattr(priceMod, "circuitBreaker", fakeCircuit)

    async def fakeFetchPriceFail(stockCode, client, *, market):
        raise GatherError("simulated source failure")

    async def fakeFetchPriceOk(stockCode, client, *, market):
        from dartlab.gather.types import PriceSnapshot

        return PriceSnapshot(current=70000.0, change=0.0, change_pct=0.0)

    def fakeLoadDomain(name: str):
        mod = types.SimpleNamespace()
        if name == "naver":
            mod.fetchPrice = fakeFetchPriceFail
        else:
            mod.fetchPrice = fakeFetchPriceOk
        return mod

    monkeypatch.setattr(priceMod, "loadDomain", fakeLoadDomain)

    async def runner():
        return await priceMod.fetch("005930", market="KR", client=object())

    result = asyncio.run(runner())
    assert result is not None

    fallbackEmits = [c for c in captured if c[0] == "gather:fallback"]
    assert len(fallbackEmits) == 1
    _, kwargs = fallbackEmits[0]
    assert kwargs["axis"] == "price"
    assert kwargs["primary"] == "naver"
    assert kwargs["fallback"] == "yahooChart"


def test_price_fallback_no_emit_when_last_source(monkeypatch: pytest.MonkeyPatch) -> None:
    """마지막 source 실패 시에는 fallback emit 안 함 — 다음 source 가 없음."""
    from dartlab.gather.infra import telemetry as telemetryMod
    from dartlab.gather.sources import price as priceMod
    from dartlab.gather.types import GatherError

    captured: list = []
    monkeypatch.setattr(telemetryMod, "_coreEmit", lambda k, **kw: captured.append((k, kw)))

    monkeypatch.setattr(priceMod, "getPriceFallback", lambda market: ["naver"])

    fakeHealth = types.SimpleNamespace(reorder=lambda chain: chain, record=lambda *a, **kw: None)
    fakeCircuit = types.SimpleNamespace(
        isOpen=lambda src: False,
        recordFailure=lambda src: None,
        recordSuccess=lambda src: None,
    )
    monkeypatch.setattr(priceMod, "healthTracker", fakeHealth)
    monkeypatch.setattr(priceMod, "circuitBreaker", fakeCircuit)

    async def fakeFail(stockCode, client, *, market):
        raise GatherError("only source failed")

    def fakeLoadDomain(name: str):
        mod = types.SimpleNamespace()
        mod.fetchPrice = fakeFail
        return mod

    monkeypatch.setattr(priceMod, "loadDomain", fakeLoadDomain)

    async def runner():
        return await priceMod.fetch("005930", market="KR", client=object())

    asyncio.run(runner())

    fallbackEmits = [c for c in captured if c[0] == "gather:fallback"]
    assert len(fallbackEmits) == 0

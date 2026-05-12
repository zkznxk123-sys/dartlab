"""dartlab.gather.entry.providerAdapter real unit test (A 트랙 S1+T1).

GatherProvider Protocol 구현체 + Gather 싱글턴 진입점의 thread-safety 와
delegation 동작 검증.
"""

from __future__ import annotations

import importlib
import threading

import pytest

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    """``dartlab.gather.entry.providerAdapter`` 모듈 import 가능 — 모듈 구조 회귀 차단."""
    importlib.import_module("dartlab.gather.entry.providerAdapter")


def test_getDefaultGather_returns_singleton() -> None:
    """순차 호출 시 동일 instance — 캐시 + HTTP client 재사용 보장."""
    from dartlab.gather.entry.providerAdapter import getDefaultGather

    g1 = getDefaultGather()
    g2 = getDefaultGather()
    assert g1 is g2


def test_getDefaultGather_thread_safe() -> None:
    """20 thread × 5 호출 동시 진입 시에도 단일 instance — double-checked lock 검증."""
    from dartlab.gather.entry import providerAdapter

    providerAdapter._defaultGather = None

    instances: list[object] = []
    barrier = threading.Barrier(20)

    def worker() -> None:
        barrier.wait()
        for _ in range(5):
            instances.append(providerAdapter.getDefaultGather())

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(instances) == 100
    assert len({id(g) for g in instances}) == 1


def test_adapter_news_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    """_GatherProviderAdapter.news 가 getDefaultGather().news 위임 — 인자 forwarding 검증."""
    from dartlab.gather.entry import providerAdapter

    captured: dict = {}

    class _FakeGather:
        def news(self, query: str, *, market: str = "KR", days: int = 30):
            captured["args"] = (query, market, days)
            return "fake-df"

    monkeypatch.setattr(providerAdapter, "getDefaultGather", lambda: _FakeGather())

    adapter = providerAdapter._GatherProviderAdapter()
    result = adapter.news("삼성전자", market="KR", days=7)

    assert result == "fake-df"
    assert captured["args"] == ("삼성전자", "KR", 7)


def test_adapter_entry_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    """_GatherProviderAdapter.entry 가 GatherEntry() callable 위임 — axis/stockCode 분기 검증."""
    from dartlab.gather.entry import providerAdapter

    captured: list = []

    class _FakeEntry:
        def __call__(self, *args, **kwargs):
            captured.append((args, kwargs))
            return "fake-result"

    monkeypatch.setattr(providerAdapter, "GatherEntry", _FakeEntry)

    adapter = providerAdapter._GatherProviderAdapter()
    adapter.entry()
    adapter.entry("price")
    adapter.entry("price", "005930", market="KR")

    assert captured[0] == ((), {})
    assert captured[1] == (("price",), {})
    assert captured[2] == (("price", "005930"), {"market": "KR"})

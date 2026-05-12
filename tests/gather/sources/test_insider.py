"""dartlab.gather.sources.insider real unit test (A 트랙 I2 + T2).

iterFetchInsiderTrading / iterFetchMajorShareholders generator 검증.
"""

from __future__ import annotations

import importlib

import pytest

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    """``dartlab.gather.sources.insider`` 모듈 import 가능 — 모듈 구조 회귀 차단."""
    importlib.import_module("dartlab.gather.sources.insider")


def test_iterFetchInsiderTrading_yields(monkeypatch: pytest.MonkeyPatch) -> None:
    """iterFetchInsiderTrading — runAsync(fetchInsiderTrading) 결과 mock 후 batch yield."""
    from dartlab.gather.sources import insider as insiderMod

    fakeRows = list(range(15))  # InsiderTrade 대신 단순 int (구조만 검증)

    async def fakeFetch(stockCode, *, market="KR"):
        return fakeRows

    monkeypatch.setattr(insiderMod, "fetchInsiderTrading", fakeFetch)

    batches = list(insiderMod.iterFetchInsiderTrading("005930", batchSize=7))
    assert len(batches) == 3  # 15 / 7 = 3 batches (7, 7, 1)
    assert len(batches[0]) == 7
    assert len(batches[-1]) == 1


def test_iterFetchMajorShareholders_yields(monkeypatch: pytest.MonkeyPatch) -> None:
    """iterFetchMajorShareholders — list batch yield."""
    from dartlab.gather.sources import insider as insiderMod

    fakeHolders = list(range(8))

    async def fakeFetch(stockCode, *, market="KR"):
        return fakeHolders

    monkeypatch.setattr(insiderMod, "fetchMajorShareholders", fakeFetch)

    batches = list(insiderMod.iterFetchMajorShareholders("005930", batchSize=3))
    assert len(batches) == 3  # 8 / 3 = 3 batches (3, 3, 2)
    assert len(batches[-1]) == 2


def test_iter_empty_returns_no_batches(monkeypatch: pytest.MonkeyPatch) -> None:
    """fetch 결과가 빈 list 면 iter 도 빈 yield."""
    from dartlab.gather.sources import insider as insiderMod

    async def fakeFetch(stockCode, *, market="KR"):
        return []

    monkeypatch.setattr(insiderMod, "fetchInsiderTrading", fakeFetch)
    monkeypatch.setattr(insiderMod, "fetchMajorShareholders", fakeFetch)

    assert list(insiderMod.iterFetchInsiderTrading("005930")) == []
    assert list(insiderMod.iterFetchMajorShareholders("005930")) == []

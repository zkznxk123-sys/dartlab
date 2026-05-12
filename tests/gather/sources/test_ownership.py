"""dartlab.gather.sources.ownership real unit test (A 트랙 I2).

iterFetch generator + _cleanFloat 헬퍼 검증.
"""

from __future__ import annotations

import importlib

import pytest

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    """``dartlab.gather.sources.ownership`` 모듈 import 가능 — 모듈 구조 회귀 차단."""
    importlib.import_module("dartlab.gather.sources.ownership")


def test_iterFetch_yields(monkeypatch: pytest.MonkeyPatch) -> None:
    """iterFetch — fetch 결과 mock 후 batch yield (A 트랙 I2)."""
    from dartlab.gather.sources import ownership as ownerMod

    fakeOwners = list(range(10))

    async def fakeFetch(stockCode, *, market="KR", client, limit=None):
        return fakeOwners

    monkeypatch.setattr(ownerMod, "fetch", fakeFetch)

    batches = list(ownerMod.iterFetch("005930", client=object(), batchSize=4))
    assert len(batches) == 3  # 10 / 4 = 3 batches (4, 4, 2)
    assert len(batches[0]) == 4
    assert len(batches[-1]) == 2


def test_cleanFloat_parses_comma_and_pct() -> None:
    """_cleanFloat — 콤마 + 공백 + 비숫자 처리."""
    from dartlab.gather.sources.ownership import _cleanFloat

    assert _cleanFloat("1,234.5") == 1234.5
    assert _cleanFloat("  42  ") == 42.0
    assert _cleanFloat("") == 0.0
    assert _cleanFloat(None) == 0.0
    assert _cleanFloat("invalid") == 0.0


def test_iterFetch_empty_returns_no_batches(monkeypatch: pytest.MonkeyPatch) -> None:
    """fetch 가 빈 list 반환 시 iter 도 빈 yield."""
    from dartlab.gather.sources import ownership as ownerMod

    async def fakeFetch(stockCode, *, market="KR", client, limit=None):
        return []

    monkeypatch.setattr(ownerMod, "fetch", fakeFetch)
    assert list(ownerMod.iterFetch("005930", client=object())) == []

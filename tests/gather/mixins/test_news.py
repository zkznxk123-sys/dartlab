"""dartlab.gather.mixins.news real unit test (A 트랙 O3).

_GatherNewsMixin 의 news/dartDoc 2 메서드 emit wrap 검증.
"""

from __future__ import annotations

import importlib

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    """``dartlab.gather.mixins.news`` 모듈 import 가능 — 모듈 구조 회귀 차단."""
    importlib.import_module("dartlab.gather.mixins.news")


def test_news_emits_gather_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    """news() 가 fetch 완료 시 emitGatherFetch 신호."""
    from dartlab.gather.engine import Gather
    from dartlab.gather.infra import telemetry as telemetryMod
    from dartlab.gather.sources import news as newsMod

    captured: list = []
    monkeypatch.setattr(telemetryMod, "_coreEmit", lambda k, **kw: captured.append((k, kw)))

    async def fakeFetchAsync(query, *, market, days, client):
        return []

    monkeypatch.setattr(newsMod, "_fetchAsync", fakeFetchAsync)
    monkeypatch.setattr(newsMod, "toDataFrame", lambda items: pl.DataFrame())

    g = Gather()
    g.news("삼성전자", market="KR", days=7)

    fetchEmits = [c for c in captured if c[0] == "gather:fetch:done"]
    assert any(kw["axis"] == "news" for _, kw in fetchEmits)

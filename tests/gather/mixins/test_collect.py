"""dartlab.gather.mixins.collect real unit test (A 트랙 O3).

_GatherCollectMixin 의 collect() emit wrap 검증.
"""

from __future__ import annotations

import importlib

import pytest

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    """``dartlab.gather.mixins.collect`` 모듈 import 가능 — 모듈 구조 회귀 차단."""
    importlib.import_module("dartlab.gather.mixins.collect")


def test_collect_emits_gather_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    """collect() 가 fetch 완료 시 emitGatherFetch 신호."""
    from datetime import datetime, timezone

    from dartlab.gather.engine import Gather
    from dartlab.gather.infra import telemetry as telemetryMod
    from dartlab.gather.mixins import collect as collectMod
    from dartlab.gather.types import GatherSnapshot

    captured: list = []
    monkeypatch.setattr(telemetryMod, "_coreEmit", lambda k, **kw: captured.append((k, kw)))

    async def fakeCollect(self, stockCode, market):
        return GatherSnapshot(
            stockCode=stockCode,
            results={},
            collected_at=datetime.now(timezone.utc).isoformat(),
            _news=[],
            _sectorInfo=None,
            _insiderTrades=[],
        )

    monkeypatch.setattr(collectMod._GatherCollectMixin, "_collectAsync", fakeCollect)

    g = Gather()
    g.collect("005930", market="KR")

    fetchEmits = [c for c in captured if c[0] == "gather:fetch:done"]
    assert any(kw["axis"] == "collect" for _, kw in fetchEmits)

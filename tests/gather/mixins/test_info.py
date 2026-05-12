"""dartlab.gather.mixins.info real unit test (A 트랙 O3).

_GatherInfoMixin 의 7 메서드 emit wrap 검증 — 대표 케이스 dividends().
"""

from __future__ import annotations

import importlib

import pytest

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    """``dartlab.gather.mixins.info`` 모듈 import 가능 — 모듈 구조 회귀 차단."""
    importlib.import_module("dartlab.gather.mixins.info")


def test_dividends_emits_gather_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    """dividends() 가 fetch 완료 시 emitGatherFetch 신호 — try/finally wrap 검증."""
    from dartlab.gather import domains as domainsMod
    from dartlab.gather.engine import Gather
    from dartlab.gather.infra import telemetry as telemetryMod

    captured: list = []
    monkeypatch.setattr(telemetryMod, "_coreEmit", lambda k, **kw: captured.append((k, kw)))

    # cache miss 분기 — DIVIDENDS_FALLBACK 빈 list 로 즉시 빈 결과
    monkeypatch.setattr(domainsMod, "DIVIDENDS_FALLBACK", [])

    g = Gather()
    g.dividends("005930", market="KR")

    fetchEmits = [c for c in captured if c[0] == "gather:fetch:done"]
    assert len(fetchEmits) >= 1
    axes = [kw["axis"] for _, kw in fetchEmits]
    assert "dividends" in axes

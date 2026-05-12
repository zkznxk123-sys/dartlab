"""dartlab.gather.mixins.macro real unit test (A 트랙 O3).

_GatherMacroMixin 의 _macroKR / _macroUS emit wrap 검증.
"""

from __future__ import annotations

import importlib

import pytest

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    """``dartlab.gather.mixins.macro`` 모듈 import 가능 — 모듈 구조 회귀 차단."""
    importlib.import_module("dartlab.gather.mixins.macro")


def test_macroKR_emits_when_apiKey_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """_macroKR 가 try/finally 안 emit — HF 경로 실패해도 emit 발동."""
    from dartlab.gather.bulkData import macroHf as macroHfMod
    from dartlab.gather.engine import Gather
    from dartlab.gather.infra import telemetry as telemetryMod

    captured: list = []
    monkeypatch.setattr(telemetryMod, "_coreEmit", lambda k, **kw: captured.append((k, kw)))

    def boom(*a, **kw):
        raise RuntimeError("HF fail")

    monkeypatch.setattr(macroHfMod, "fetchMulti", boom)

    g = Gather()
    g.macro("KR")

    axes = [kw["axis"] for k, kw in captured if k == "gather:fetch:done"]
    assert "macroKR" in axes or "macro" in axes

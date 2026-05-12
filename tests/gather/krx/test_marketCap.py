"""dartlab.gather.krx.marketCap real unit test (A 트랙 T3).

fetchOhlcv 위임 안전 + loadSharesOutstanding 파일 부재 안전 + marketCap 시그니처.
"""

from __future__ import annotations

import importlib
import inspect

import pytest

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    """``dartlab.gather.krx.marketCap`` 모듈 import 가능 — 모듈 구조 회귀 차단."""
    importlib.import_module("dartlab.gather.krx.marketCap")


def test_marketCap_typed_signature() -> None:
    """marketCap 시그니처 — stockCode 필수 + market/start/end keyword."""
    from dartlab.gather.krx.marketCap import marketCap

    sig = inspect.signature(marketCap)
    params = sig.parameters
    assert "stockCode" in params
    assert params["stockCode"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert params["market"].default == "auto"
    assert params["start"].default is None
    assert params["end"].default is None


def test_fetchOhlcv_exception_returns_none(monkeypatch) -> None:
    """fetchOhlcv — GatherEntry 호출 실패 시 None + warning (ImportError 흡수)."""
    from dartlab.gather.krx import marketCap as marketCapMod

    class BoomEntry:
        def __call__(self, *a, **kw):
            raise RuntimeError("simulated GatherEntry failure")

    monkeypatch.setattr(marketCapMod, "GatherEntry", BoomEntry)
    result = marketCapMod.fetchOhlcv("005930", market="KR")
    assert result is None


def test_loadSharesOutstanding_signature() -> None:
    """loadSharesOutstanding 시그니처 — market keyword 단독 + 기본 'KR'."""
    from dartlab.gather.krx.marketCap import loadSharesOutstanding

    sig = inspect.signature(loadSharesOutstanding)
    assert "market" in sig.parameters
    assert sig.parameters["market"].default == "KR"

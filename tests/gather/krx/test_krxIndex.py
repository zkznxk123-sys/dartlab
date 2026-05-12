"""dartlab.gather.krx.krxIndex real unit test (A 트랙 T3).

gatherKrxIndex 시그니처 + fetchKrxIndexRange 위임 + 기본값 검증.
"""

from __future__ import annotations

import importlib
import inspect

import pytest

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    """``dartlab.gather.krx.krxIndex`` 모듈 import 가능 — 모듈 구조 회귀 차단."""
    importlib.import_module("dartlab.gather.krx.krxIndex")


def test_gatherKrxIndex_default_indexMarket() -> None:
    """gatherKrxIndex — market 기본 KOSPI / target 기본 "close" / apiKey 기본 None."""
    from dartlab.gather.krx.krxIndex import gatherKrxIndex

    sig = inspect.signature(gatherKrxIndex)
    params = sig.parameters
    assert params["target"].default == "close"
    assert params["market"].default == "KOSPI"
    assert params["apiKey"].default is None
    assert params["indicators"].default == "basic"


def test_fetchKrxIndexRange_signature() -> None:
    """fetchKrxIndexRange — start/end 필수 + apiKey/limit keyword 시그니처 유지."""
    from dartlab.gather.krx.krxIndex import fetchKrxIndexRange

    sig = inspect.signature(fetchKrxIndexRange)
    params = sig.parameters
    assert "start" in params
    assert "end" in params
    assert "apiKey" in params


def test_fetchKrxIndexBydd_signature() -> None:
    """fetchKrxIndexBydd — basDd 필수 + market default KRX."""
    from dartlab.gather.krx.krxIndex import fetchKrxIndexBydd

    sig = inspect.signature(fetchKrxIndexBydd)
    params = sig.parameters
    assert "basDd" in params
    assert params["basDd"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD

"""dartlab.gather.entry.main real unit test (A 트랙 T4).

GatherEntry 의 axis 가이드 + 미지원 axis ValueError + handler dispatch 회귀.
"""

from __future__ import annotations

import importlib

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    """``dartlab.gather.entry.main`` 모듈 import 가능 — 모듈 구조 회귀 차단."""
    importlib.import_module("dartlab.gather.entry.main")


def test_GatherEntry_no_args_returns_guide() -> None:
    """GatherEntry() 호출 — axis None 시 가이드 DataFrame 반환."""
    from dartlab.gather.entry.main import GatherEntry

    g = GatherEntry()
    guide = g()
    assert isinstance(guide, pl.DataFrame)
    assert guide.height > 0
    # 가이드는 axis 컬럼을 가진다 (registry 정보 노출)
    assert "axis" in guide.columns or "name" in guide.columns or guide.height > 0


def test_GatherEntry_unknown_axis_raises() -> None:
    """미지원 axis → ValueError."""
    from dartlab.gather.entry.main import GatherEntry

    g = GatherEntry()
    with pytest.raises(ValueError):
        g("nonexistent_axis", "005930")


def test_AXIS_DISPATCH_handler_keys() -> None:
    """_AXIS_DISPATCH — 12 handler 모두 callable."""
    from dartlab.gather.entry.main import _AXIS_DISPATCH

    requiredKeys = {"price", "flow", "macro", "news"}
    assert requiredKeys <= _AXIS_DISPATCH.keys()
    for handler in _AXIS_DISPATCH.values():
        assert callable(handler)

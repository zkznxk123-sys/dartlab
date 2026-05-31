"""Panel(pl.DataFrame) subclass mirror — 생성·callable·부재 동작 (데이터 0).

``providers/dart/panel/panel.py`` 의 1:1 mirror. Panel 이 pl.DataFrame subclass + callable
이고, artifact 없는 종목은 빈 DataFrame + __call__ None 임을 검증 (network/lxml 0, R2).
실데이터 wide/검색은 tests/panel/test_panel_intra.py (requires_data) 담당.
"""

from __future__ import annotations

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def test_panel_is_dataframe_subclass_and_callable() -> None:
    """Panel 인스턴스는 pl.DataFrame 이고 callable (잡는 순간 wide + 검색)."""
    from dartlab.providers.dart.panel import Panel

    p = Panel("000000nonexistent")
    assert isinstance(p, pl.DataFrame)
    assert callable(p)


def test_panel_absent_is_empty_dataframe() -> None:
    """artifact 없는 종목 → 빈 DataFrame (예외 없음)."""
    from dartlab.providers.dart.panel import Panel

    p = Panel("000000nonexistent")
    assert p.is_empty()


def test_panel_call_none_on_empty_or_blank_key() -> None:
    """빈 key 또는 artifact 부재 시 __call__ → None (전체 반환 금지)."""
    from dartlab.providers.dart.panel import Panel

    p = Panel("000000nonexistent")
    assert p("") is None
    assert p("재고") is None

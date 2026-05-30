"""Panel facade mirror — 상태없는 read·artifact 부재 동작 (데이터 0).

``providers/dart/panel/panel.py`` 의 1:1 mirror. Panel 생성·context·artifact 없는 종목의
None/빈 반환을 검증 (network/lxml 0, R2). 실데이터 board/show 는 tests/panel/ (requires_data).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_panel_construct_and_context() -> None:
    """Panel 생성 + with context (상태 없음, 부작용 0)."""
    from dartlab.providers.dart.panel import Panel

    with Panel("005930") as p:
        assert p.code == "005930"
        assert p.marketNs == "kr"


def test_panel_absent_returns_empty_and_none() -> None:
    """artifact 없는 종목 → periods() 빈 list, board/wide/long None."""
    from dartlab.providers.dart.panel import Panel

    p = Panel("000000nonexistent")
    assert p.periods() == []
    assert p.board() is None
    assert p.wide() is None
    assert p.long() is None
    assert p.show("inventoryDisclosure") is None

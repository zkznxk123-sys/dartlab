"""panel pivot (회사내 수평화) mirror — artifact 부재 None 경로 (데이터 0).

``providers/dart/panel/pivot.py`` 의 1:1 mirror. readPanelWide/readMeta 가 artifact 없는
종목에 None 을 반환하는지 검증. 실데이터 위 수평화 동작은 tests/panel/test_panel_intra.py
(requires_data) 가 담당.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_read_panel_wide_none_when_absent() -> None:
    """artifact 없는 종목 → readPanelWide None."""
    from dartlab.providers.dart.panel.pivot import readPanelWide

    assert readPanelWide("000000nonexistent") is None


def test_read_meta_none_when_absent() -> None:
    """artifact 없는 종목 → readMeta None (board)."""
    from dartlab.providers.dart.panel.pivot import readMeta

    assert readMeta("000000nonexistent") is None

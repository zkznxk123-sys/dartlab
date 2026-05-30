"""panel reader (scan_parquet lazy / long) mirror — artifact 부재 None 경로 (데이터 0).

``providers/dart/panel/reader.py`` 의 1:1 mirror. artifact 없는 종목코드로 None 경로를
검증 (read 층은 network/lxml 0, R2). _panelDir 경로 SSOT 도 확인.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_panel_dir_path_market_namespace() -> None:
    """_panelDir: kr→dart/panel, us→edgar/panel."""
    from dartlab.providers.dart.panel.reader import _panelDir

    assert _panelDir("005930", "kr").as_posix().endswith("dart/panel/005930")
    assert _panelDir("AAPL", "us").as_posix().endswith("edgar/panel/AAPL")


def test_scan_and_read_none_when_absent() -> None:
    """존재하지 않는 종목 → scanPanel/readLong 모두 None (데이터 로드 0)."""
    from dartlab.providers.dart.panel.reader import readLong, scanPanel

    assert scanPanel("000000nonexistent") is None
    assert readLong("000000nonexistent") is None

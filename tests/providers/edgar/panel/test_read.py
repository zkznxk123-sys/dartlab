"""EDGAR panel read facade — DART read 계약을 US 기본으로 미러."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_read_facade_defaults_to_us(builtTicker) -> None:
    from dartlab.providers.edgar.panel.build.builder import buildEdgarPanel
    from dartlab.providers.edgar.panel.read import readLong, readWide

    from .synthData import synthSubmissionTxt

    buildEdgarPanel(builtTicker, [{"text": synthSubmissionTxt()}])

    long = readLong("test")
    wide = readWide("test")
    assert long is not None and not long.is_empty()
    assert wide is not None and not wide.is_empty()
    assert long["corp"].unique().to_list() == ["TEST"]
    assert "2024Q4" in wide.columns


def test_read_facade_exports_shared_backbone() -> None:
    import dartlab.providers.edgar.panel.read as read

    for name in (
        "scopeExpr",
        "anchorLatest",
        "alignNotes",
        "absorbAttached",
        "anchorNarrativeToSpine",
        "orderBySpine",
    ):
        assert hasattr(read, name)

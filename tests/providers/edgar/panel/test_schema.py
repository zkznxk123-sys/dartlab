"""EDGAR panel schema facade — DART 16-col 계약과 같은 객체를 노출."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_schema_facade_is_dart_panel_contract() -> None:
    from dartlab.providers.dart.panel.schema import PANEL_SCHEMA as DART_PANEL_SCHEMA
    from dartlab.providers.dart.panel.schema import PIVOT_INDEX as DART_PIVOT_INDEX
    from dartlab.providers.edgar.panel.schema import PANEL_SCHEMA, PIVOT_INDEX

    assert PANEL_SCHEMA is DART_PANEL_SCHEMA
    assert PIVOT_INDEX is DART_PIVOT_INDEX
    assert len(PANEL_SCHEMA) == 16

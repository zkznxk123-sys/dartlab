"""EDGAR native payload — 별도 panelCell 없이 panel contentRaw 에서 encode/decode."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_native_payload_roundtrip() -> None:
    from dartlab.providers.edgar.panel.native import decodeNativeCellsPayload, encodeNativeCellsPayload

    cells = [{"statement": "IS", "concept": "Revenues", "valueRaw": "123"}]
    payload = encodeNativeCellsPayload(cells)
    assert decodeNativeCellsPayload(payload) == cells

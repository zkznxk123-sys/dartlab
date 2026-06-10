"""관세청 catalog 회귀 — gather/customs/catalog.py (네트워크 없음)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_catalog_entries_and_lookup() -> None:
    from dartlab.gather.customs import getAllEntries, getEntry

    entries = getAllEntries()
    assert len(entries) >= 15
    assert getEntry("8542").group == "반도체"
    assert getEntry("0000") is None
    ids = [e.id for e in entries]
    assert len(ids) == len(set(ids)), "HS id 중복"

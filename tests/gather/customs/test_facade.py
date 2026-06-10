"""관세청 facade 회귀 — gather/customs/facade.py (명시 키, 네트워크 없음)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_facade_catalog_no_network() -> None:
    from dartlab.gather.customs import Customs, getAllEntries

    c = Customs(apiKey="dummy")  # 명시 키 — resolveKey 무네트워크
    assert c.catalog("반도체").height == 2
    full = c.catalog()
    assert full.height == len(getAllEntries())
    assert set(full.columns) == {"id", "label", "group", "frequency", "unit", "description"}

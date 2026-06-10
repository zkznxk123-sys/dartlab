"""관세청 타입 회귀 — gather/customs/types.py."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_catalogEntry_fields() -> None:
    from dartlab.gather.customs.types import CatalogEntry

    e = CatalogEntry("8542", "반도체", "반도체", "Monthly", "USD", "집적회로")
    assert e.id == "8542" and e.unit == "USD"


def test_error_hierarchy() -> None:
    from dartlab.gather.customs.types import CustomsError, RateLimitError

    assert issubclass(RateLimitError, CustomsError)

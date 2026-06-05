"""EDGAR panel compare facade — DART compare 공개 표면 mirror."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_compare_facade_exports_callable() -> None:
    from dartlab.providers.edgar.panel import compare
    from dartlab.providers.edgar.panel.compare import compare as compareModule

    assert compare is compareModule
    assert callable(compare)

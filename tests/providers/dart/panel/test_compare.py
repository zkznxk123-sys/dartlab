"""DART panel compare — 공개 compare 표면 mirror 슬롯."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_compare_public_surface_callable() -> None:
    from dartlab.providers.dart.panel import compare
    from dartlab.providers.dart.panel.compare import compare as compareModule

    assert compare is compareModule
    assert callable(compare)

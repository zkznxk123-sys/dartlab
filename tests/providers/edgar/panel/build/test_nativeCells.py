"""EDGAR nativeCells builder — panel 단일 artifact payload 용 셀 row 생성."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_build_native_cells_empty_inputs() -> None:
    from dartlab.providers.edgar.panel.build.nativeCells import buildNativeCells

    meta = {"ticker": "TEST", "accession": "0000012345-25-000001", "filingPeriod": "2024Q4"}
    assert buildNativeCells([], {}, {}, {}, meta=meta) == []

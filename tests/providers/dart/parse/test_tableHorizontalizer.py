"""providers/dart/parse/tableHorizontalizer.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.parse.tableHorizontalizer  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_horizontalize_table_block_callable() -> None:
    """horizontalizeTableBlock() callable smoke."""
    from dartlab.providers.dart.parse.tableHorizontalizer import horizontalizeTableBlock

    assert callable(horizontalizeTableBlock)


def test_strip_unit_header_callable() -> None:
    """stripUnitHeader() callable smoke."""
    from dartlab.providers.dart.parse.tableHorizontalizer import stripUnitHeader

    assert callable(stripUnitHeader)

"""providers/dart/docs/sections/tableParser.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.sections.tableParser  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_build_table_data_frame_callable() -> None:
    """buildTableDataFrame() callable smoke."""
    from dartlab.providers.dart.docs.sections.tableParser import buildTableDataFrame

    assert callable(buildTableDataFrame)


def test_split_subtables_callable() -> None:
    """splitSubtables() callable smoke."""
    from dartlab.providers.dart.docs.sections.tableParser import splitSubtables

    assert callable(splitSubtables)

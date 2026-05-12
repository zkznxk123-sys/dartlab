"""providers/dart/docs/finance/segment/parser.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.segment.parser  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_classify_table_callable() -> None:
    """classifyTable() callable smoke."""
    from dartlab.providers.dart.docs.finance.segment.parser import classifyTable

    assert callable(classifyTable)


def test_is_data_row_callable() -> None:
    """isDataRow() callable smoke."""
    from dartlab.providers.dart.docs.finance.segment.parser import isDataRow

    assert callable(isDataRow)


def test_is_header_row_callable() -> None:
    """isHeaderRow() callable smoke."""
    from dartlab.providers.dart.docs.finance.segment.parser import isHeaderRow

    assert callable(isHeaderRow)


def test_merge_headers_callable() -> None:
    """mergeHeaders() callable smoke."""
    from dartlab.providers.dart.docs.finance.segment.parser import mergeHeaders

    assert callable(mergeHeaders)


def test_parse_segment_tables_callable() -> None:
    """parseSegmentTables() callable smoke."""
    from dartlab.providers.dart.docs.finance.segment.parser import parseSegmentTables

    assert callable(parseSegmentTables)

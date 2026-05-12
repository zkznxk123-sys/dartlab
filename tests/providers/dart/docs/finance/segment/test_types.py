"""providers/dart/docs/finance/segment/types.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.segment.types  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_to_data_frame_callable() -> None:
    """toDataFrame() callable smoke."""
    from dartlab.providers.dart.docs.finance.segment.types import SegmentTable

    assert hasattr(SegmentTable, "toDataFrame")


def test_latest_table_callable() -> None:
    """latestTable() callable smoke."""
    from dartlab.providers.dart.docs.finance.segment.types import SegmentsResult

    assert hasattr(SegmentsResult, "latestTable")

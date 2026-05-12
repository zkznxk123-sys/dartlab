"""providers/dart/builder/dataShapeUtils.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    import dartlab.providers.dart.builder.dataShapeUtils  # noqa: F401


def test_apply_period_filter_callable() -> None:
    """applyPeriodFilter() callable smoke."""
    from dartlab.providers.dart.builder.dataShapeUtils import applyPeriodFilter

    assert callable(applyPeriodFilter)


def test_clean_finance_data_frame_callable() -> None:
    """cleanFinanceDataFrame() callable smoke."""
    from dartlab.providers.dart.builder.dataShapeUtils import cleanFinanceDataFrame

    assert callable(cleanFinanceDataFrame)


def test_transpose_to_vertical_callable() -> None:
    """transposeToVertical() callable smoke."""
    from dartlab.providers.dart.builder.dataShapeUtils import transposeToVertical

    assert callable(transposeToVertical)


def test_warn_unknown_topic_callable() -> None:
    """warnUnknownTopic() callable smoke."""
    from dartlab.providers.dart.builder.dataShapeUtils import warnUnknownTopic

    assert callable(warnUnknownTopic)

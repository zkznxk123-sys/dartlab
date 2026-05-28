"""providers/dart/docs/sections/sectionsBase.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.sectionsArchive.sectionsBase  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_base_path_callable() -> None:
    """basePath() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.sectionsBase import basePath

    assert callable(basePath)


def test_detect_content_col_callable() -> None:
    """detectContentCol() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.sectionsBase import detectContentCol

    assert callable(detectContentCol)


def test_display_period_callable() -> None:
    """displayPeriod() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.sectionsBase import displayPeriod

    assert callable(displayPeriod)


def test_format_period_range_callable() -> None:
    """formatPeriodRange() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.sectionsBase import formatPeriodRange

    assert callable(formatPeriodRange)


def test_period_columns_callable() -> None:
    """periodColumns() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.sectionsBase import periodColumns

    assert callable(periodColumns)


def test_period_order_value_callable() -> None:
    """periodOrderValue() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.sectionsBase import periodOrderValue

    assert callable(periodOrderValue)


def test_period_sort_key_callable() -> None:
    """periodSortKey() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.sectionsBase import periodSortKey

    assert callable(periodSortKey)


def test_raw_period_callable() -> None:
    """rawPeriod() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.sectionsBase import rawPeriod

    assert callable(rawPeriod)


def test_reorder_period_columns_callable() -> None:
    """reorderPeriodColumns() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.sectionsBase import reorderPeriodColumns

    assert callable(reorderPeriodColumns)


def test_sort_periods_callable() -> None:
    """sortPeriods() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.sectionsBase import sortPeriods

    assert callable(sortPeriods)

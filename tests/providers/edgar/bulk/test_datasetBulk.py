"""providers/edgar/bulk/datasetBulk.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.bulk.datasetBulk  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_convert_quarterly_to_parquets_callable() -> None:
    """convertQuarterlyToParquets() callable smoke."""
    from dartlab.providers.edgar.bulk.datasetBulk import convertQuarterlyToParquets

    assert callable(convertQuarterlyToParquets)


def test_discover_latest_quarter_callable() -> None:
    """discoverLatestQuarter() callable smoke."""
    from dartlab.providers.edgar.bulk.datasetBulk import discoverLatestQuarter

    assert callable(discoverLatestQuarter)


def test_download_quarterly_dataset_callable() -> None:
    """downloadQuarterlyDataset() callable smoke."""
    from dartlab.providers.edgar.bulk.datasetBulk import downloadQuarterlyDataset

    assert callable(downloadQuarterlyDataset)


def test_iter_local_quarters_callable() -> None:
    """iterLocalQuarters() callable smoke."""
    from dartlab.providers.edgar.bulk.datasetBulk import iterLocalQuarters

    assert callable(iterLocalQuarters)


def test_list_local_quarters_callable() -> None:
    """listLocalQuarters() callable smoke."""
    from dartlab.providers.edgar.bulk.datasetBulk import listLocalQuarters

    assert callable(listLocalQuarters)

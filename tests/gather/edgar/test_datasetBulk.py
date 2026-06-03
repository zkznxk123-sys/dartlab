"""gather/edgar/datasetBulk.py mirror smoke — SEC 분기 zip download fetch.

수집 일원화: 분기 financial-statement-data-sets zip download(fetch)는 gather 전담.
TSV 파싱·parquet 변환(build)·로컬 조회(read)는 providers/edgar/bulk/datasetBulk.
"""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.gather.edgar.datasetBulk  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_discover_latest_quarter_callable() -> None:
    """discoverLatestQuarter() callable smoke."""
    from dartlab.gather.edgar.datasetBulk import discoverLatestQuarter

    assert callable(discoverLatestQuarter)


def test_download_quarterly_dataset_callable() -> None:
    """downloadQuarterlyDataset() callable smoke."""
    from dartlab.gather.edgar.datasetBulk import downloadQuarterlyDataset

    assert callable(downloadQuarterlyDataset)


def test_core_delegate_routes_to_gather() -> None:
    """core.edgarClient delegate → gather/edgar/datasetBulk (providers↛gather seam)."""
    from dartlab.core.edgarClient import discoverLatestQuarter, downloadQuarterlyDataset

    assert callable(discoverLatestQuarter)
    assert callable(downloadQuarterlyDataset)

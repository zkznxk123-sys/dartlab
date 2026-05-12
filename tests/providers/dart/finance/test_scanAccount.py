"""providers/dart/finance/scanAccount.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.finance.scanAccount  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_scan_account_callable() -> None:
    """scanAccount() callable smoke."""
    from dartlab.providers.dart.finance.scanAccount import scanAccount

    assert callable(scanAccount)


def test_scan_account_list_callable() -> None:
    """scanAccountList() callable smoke."""
    from dartlab.providers.dart.finance.scanAccount import scanAccountList

    assert callable(scanAccountList)


def test_scan_ratio_callable() -> None:
    """scanRatio() callable smoke."""
    from dartlab.providers.dart.finance.scanAccount import scanRatio

    assert callable(scanRatio)


def test_scan_ratio_list_callable() -> None:
    """scanRatioList() callable smoke."""
    from dartlab.providers.dart.finance.scanAccount import scanRatioList

    assert callable(scanRatioList)

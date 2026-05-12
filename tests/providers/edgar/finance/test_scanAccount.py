"""providers/edgar/finance/scanAccount.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.finance.scanAccount  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_scan_account_callable() -> None:
    """scanAccount() callable smoke."""
    from dartlab.providers.edgar.finance.scanAccount import scanAccount

    assert callable(scanAccount)


def test_scan_ratio_callable() -> None:
    """scanRatio() callable smoke."""
    from dartlab.providers.edgar.finance.scanAccount import scanRatio

    assert callable(scanRatio)

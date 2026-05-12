"""providers/dart/docs/finance/shareCapital.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.shareCapital  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_build_shares_outstanding_scan_callable() -> None:
    """buildSharesOutstandingScan() callable smoke."""
    from dartlab.providers.dart.docs.finance.shareCapital import buildSharesOutstandingScan

    assert callable(buildSharesOutstandingScan)


def test_parse_share_capital_table_callable() -> None:
    """parseShareCapitalTable() callable smoke."""
    from dartlab.providers.dart.docs.finance.shareCapital import parseShareCapitalTable

    assert callable(parseShareCapitalTable)


def test_share_capital_callable() -> None:
    """shareCapital() callable smoke."""
    from dartlab.providers.dart.docs.finance.shareCapital import shareCapital

    assert callable(shareCapital)

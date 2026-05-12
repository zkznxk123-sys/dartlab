"""providers/dart/builder/scanAggregator.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    import dartlab.providers.dart.builder.scanAggregator  # noqa: F401


def test_build_scan_capital_callable() -> None:
    """buildScanCapital() callable smoke."""
    from dartlab.providers.dart.builder.scanAggregator import buildScanCapital

    assert callable(buildScanCapital)


def test_build_scan_debt_callable() -> None:
    """buildScanDebt() callable smoke."""
    from dartlab.providers.dart.builder.scanAggregator import buildScanDebt

    assert callable(buildScanDebt)


def test_build_scan_governance_callable() -> None:
    """buildScanGovernance() callable smoke."""
    from dartlab.providers.dart.builder.scanAggregator import buildScanGovernance

    assert callable(buildScanGovernance)


def test_build_scan_network_callable() -> None:
    """buildScanNetwork() callable smoke."""
    from dartlab.providers.dart.builder.scanAggregator import buildScanNetwork

    assert callable(buildScanNetwork)


def test_build_scan_workforce_callable() -> None:
    """buildScanWorkforce() callable smoke."""
    from dartlab.providers.dart.builder.scanAggregator import buildScanWorkforce

    assert callable(buildScanWorkforce)


def test_company_scan_view_callable() -> None:
    """companyScanView() callable smoke."""
    from dartlab.providers.dart.builder.scanAggregator import companyScanView

    assert callable(companyScanView)

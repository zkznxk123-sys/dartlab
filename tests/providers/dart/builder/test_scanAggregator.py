"""providers/dart/builder/scanAggregator.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    import dartlab.providers.dart.builder.scanAggregator  # noqa: F401


def testBuildScanCapitalCallable() -> None:
    """buildScanCapital() callable smoke."""
    from dartlab.providers.dart.builder.scanAggregator import buildScanCapital

    assert callable(buildScanCapital)


def testBuildScanDebtCallable() -> None:
    """buildScanDebt() callable smoke."""
    from dartlab.providers.dart.builder.scanAggregator import buildScanDebt

    assert callable(buildScanDebt)


def testBuildScanGovernanceCallable() -> None:
    """buildScanGovernance() callable smoke."""
    from dartlab.providers.dart.builder.scanAggregator import buildScanGovernance

    assert callable(buildScanGovernance)


def test_build_scan_network_callable() -> None:
    """buildScanNetwork() callable smoke."""
    from dartlab.providers.dart.builder.scanAggregator import buildScanNetwork

    assert callable(buildScanNetwork)


def testBuildScanWorkforceCallable() -> None:
    """buildScanWorkforce() callable smoke."""
    from dartlab.providers.dart.builder.scanAggregator import buildScanWorkforce

    assert callable(buildScanWorkforce)


def test_company_scan_view_callable() -> None:
    """companyScanView() callable smoke."""
    from dartlab.providers.dart.builder.scanAggregator import companyScanView

    assert callable(companyScanView)

"""providers/dart/accessor/financeDocAccessor.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    import dartlab.providers.dart.accessor.financeDocAccessor  # noqa: F401


def test_account_labels_callable() -> None:
    """accountLabels() callable smoke."""
    from dartlab.providers.dart.accessor.financeDocAccessor import DartFinanceDocAccessor

    assert hasattr(DartFinanceDocAccessor, "accountLabels")


def test_build_annual_callable() -> None:
    """buildAnnual() callable smoke."""
    from dartlab.providers.dart.accessor.financeDocAccessor import DartFinanceDocAccessor

    assert hasattr(DartFinanceDocAccessor, "buildAnnual")


def test_build_timeseries_callable() -> None:
    """buildTimeseries() callable smoke."""
    from dartlab.providers.dart.accessor.financeDocAccessor import DartFinanceDocAccessor

    assert hasattr(DartFinanceDocAccessor, "buildTimeseries")


def test_contingent_liability_callable() -> None:
    """contingentLiability() callable smoke."""
    from dartlab.providers.dart.accessor.financeDocAccessor import DartFinanceDocAccessor

    assert hasattr(DartFinanceDocAccessor, "contingentLiability")


def test_executive_callable() -> None:
    """executive() callable smoke."""
    from dartlab.providers.dart.accessor.financeDocAccessor import DartFinanceDocAccessor

    assert hasattr(DartFinanceDocAccessor, "executive")


def test_export_modules_callable() -> None:
    """exportModules() callable smoke."""
    from dartlab.providers.dart.accessor.financeDocAccessor import DartFinanceDocAccessor

    assert hasattr(DartFinanceDocAccessor, "exportModules")


def test_pivot_dividend_callable() -> None:
    """pivotDividend() callable smoke."""
    from dartlab.providers.dart.accessor.financeDocAccessor import DartFinanceDocAccessor

    assert hasattr(DartFinanceDocAccessor, "pivotDividend")


def test_related_party_tx_callable() -> None:
    """relatedPartyTx() callable smoke."""
    from dartlab.providers.dart.accessor.financeDocAccessor import DartFinanceDocAccessor

    assert hasattr(DartFinanceDocAccessor, "relatedPartyTx")


def test_sanction_callable() -> None:
    """sanction() callable smoke."""
    from dartlab.providers.dart.accessor.financeDocAccessor import DartFinanceDocAccessor

    assert hasattr(DartFinanceDocAccessor, "sanction")

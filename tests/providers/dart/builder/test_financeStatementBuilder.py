"""providers/dart/builder/financeStatementBuilder.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    import dartlab.providers.dart.builder.financeStatementBuilder  # noqa: F401


def test_aggregate_cis_annual_callable() -> None:
    """aggregateCisAnnual() callable smoke."""
    from dartlab.providers.dart.builder.financeStatementBuilder import aggregateCisAnnual

    assert callable(aggregateCisAnnual)


def test_build_finance_series_callable() -> None:
    """buildFinanceSeries() callable smoke."""
    from dartlab.providers.dart.builder.financeStatementBuilder import buildFinanceSeries

    assert callable(buildFinanceSeries)


def test_build_ratios_callable() -> None:
    """buildRatios() callable smoke."""
    from dartlab.providers.dart.builder.financeStatementBuilder import buildRatios

    assert callable(buildRatios)


def test_finance_cis_annual_callable() -> None:
    """financeCisAnnual() callable smoke."""
    from dartlab.providers.dart.builder.financeStatementBuilder import financeCisAnnual

    assert callable(financeCisAnnual)


def test_finance_cis_quarterly_callable() -> None:
    """financeCisQuarterly() callable smoke."""
    from dartlab.providers.dart.builder.financeStatementBuilder import financeCisQuarterly

    assert callable(financeCisQuarterly)


def test_finance_or_docs_statement_callable() -> None:
    """financeOrDocsStatement() callable smoke."""
    from dartlab.providers.dart.builder.financeStatementBuilder import financeOrDocsStatement

    assert callable(financeOrDocsStatement)


def test_finance_stmt_callable() -> None:
    """financeStmt() callable smoke."""
    from dartlab.providers.dart.builder.financeStatementBuilder import financeStmt

    assert callable(financeStmt)


def test_ratio_series_callable() -> None:
    """ratioSeries() callable smoke."""
    from dartlab.providers.dart.builder.financeStatementBuilder import ratioSeries

    assert callable(ratioSeries)


def test_sce_callable() -> None:
    """sce() callable smoke."""
    from dartlab.providers.dart.builder.financeStatementBuilder import sce

    assert callable(sce)


def test_sce_matrix_callable() -> None:
    """sceMatrix() callable smoke."""
    from dartlab.providers.dart.builder.financeStatementBuilder import sceMatrix

    assert callable(sceMatrix)


def test_sce_series_annual_callable() -> None:
    """sceSeriesAnnual() callable smoke."""
    from dartlab.providers.dart.builder.financeStatementBuilder import sceSeriesAnnual

    assert callable(sceSeriesAnnual)

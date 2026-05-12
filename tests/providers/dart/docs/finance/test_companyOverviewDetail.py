"""providers/dart/docs/finance/companyOverviewDetail.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.companyOverviewDetail  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_company_overview_detail_callable() -> None:
    """companyOverviewDetail() callable smoke."""
    from dartlab.providers.dart.docs.finance.companyOverviewDetail import companyOverviewDetail

    assert callable(companyOverviewDetail)


def test_is_separator_row_callable() -> None:
    """isSeparatorRow() callable smoke."""
    from dartlab.providers.dart.docs.finance.companyOverviewDetail import isSeparatorRow

    assert callable(isSeparatorRow)


def test_parse_company_info_callable() -> None:
    """parseCompanyInfo() callable smoke."""
    from dartlab.providers.dart.docs.finance.companyOverviewDetail import parseCompanyInfo

    assert callable(parseCompanyInfo)


def test_parse_company_info_fallback_callable() -> None:
    """parseCompanyInfoFallback() callable smoke."""
    from dartlab.providers.dart.docs.finance.companyOverviewDetail import parseCompanyInfoFallback

    assert callable(parseCompanyInfoFallback)


def test_split_cells_callable() -> None:
    """splitCells() callable smoke."""
    from dartlab.providers.dart.docs.finance.companyOverviewDetail import splitCells

    assert callable(splitCells)

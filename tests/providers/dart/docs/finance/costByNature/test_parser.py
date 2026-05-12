"""providers/dart/docs/finance/costByNature/parser.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.costByNature.parser  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_find_cost_by_nature_section_callable() -> None:
    """findCostByNatureSection() callable smoke."""
    from dartlab.providers.dart.docs.finance.costByNature.parser import findCostByNatureSection

    assert callable(findCostByNatureSection)


def test_is_total_row_callable() -> None:
    """isTotalRow() callable smoke."""
    from dartlab.providers.dart.docs.finance.costByNature.parser import isTotalRow

    assert callable(isTotalRow)


def test_normalize_account_name_callable() -> None:
    """normalizeAccountName() callable smoke."""
    from dartlab.providers.dart.docs.finance.costByNature.parser import normalizeAccountName

    assert callable(normalizeAccountName)


def test_parse_cost_by_nature_callable() -> None:
    """parseCostByNature() callable smoke."""
    from dartlab.providers.dart.docs.finance.costByNature.parser import parseCostByNature

    assert callable(parseCostByNature)

"""providers/dart/docs/finance/affiliateGroup.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.affiliateGroup  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_affiliate_group_callable() -> None:
    """affiliateGroup() callable smoke."""
    from dartlab.providers.dart.docs.finance.affiliateGroup import affiliateGroup

    assert callable(affiliateGroup)


def test_is_separator_row_callable() -> None:
    """isSeparatorRow() callable smoke."""
    from dartlab.providers.dart.docs.finance.affiliateGroup import isSeparatorRow

    assert callable(isSeparatorRow)


def test_parse_affiliate_list_callable() -> None:
    """parseAffiliateList() callable smoke."""
    from dartlab.providers.dart.docs.finance.affiliateGroup import parseAffiliateList

    assert callable(parseAffiliateList)


def test_parse_group_summary_callable() -> None:
    """parseGroupSummary() callable smoke."""
    from dartlab.providers.dart.docs.finance.affiliateGroup import parseGroupSummary

    assert callable(parseGroupSummary)


def test_split_cells_callable() -> None:
    """splitCells() callable smoke."""
    from dartlab.providers.dart.docs.finance.affiliateGroup import splitCells

    assert callable(splitCells)

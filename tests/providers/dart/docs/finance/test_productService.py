"""providers/dart/docs/finance/productService.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.productService  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_detect_unit_callable() -> None:
    """detectUnit() callable smoke."""
    from dartlab.providers.dart.docs.finance.productService import detectUnit

    assert callable(detectUnit)


def test_is_separator_row_callable() -> None:
    """isSeparatorRow() callable smoke."""
    from dartlab.providers.dart.docs.finance.productService import isSeparatorRow

    assert callable(isSeparatorRow)


def test_parse_amount_callable() -> None:
    """parseAmount() callable smoke."""
    from dartlab.providers.dart.docs.finance.productService import parseAmount

    assert callable(parseAmount)


def test_parse_product_service_callable() -> None:
    """parseProductService() callable smoke."""
    from dartlab.providers.dart.docs.finance.productService import parseProductService

    assert callable(parseProductService)


def test_parse_ratio_callable() -> None:
    """parseRatio() callable smoke."""
    from dartlab.providers.dart.docs.finance.productService import parseRatio

    assert callable(parseRatio)


def test_product_service_callable() -> None:
    """productService() callable smoke."""
    from dartlab.providers.dart.docs.finance.productService import productService

    assert callable(productService)


def test_split_cells_callable() -> None:
    """splitCells() callable smoke."""
    from dartlab.providers.dart.docs.finance.productService import splitCells

    assert callable(splitCells)

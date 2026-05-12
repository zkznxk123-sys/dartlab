"""providers/edgar/finance/mapper.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.finance.mapper  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_classify_tags_by_stmt_callable() -> None:
    """classifyTagsByStmt() callable smoke."""
    from dartlab.providers.edgar.finance.mapper import EdgarMapper

    assert hasattr(EdgarMapper, "classifyTagsByStmt")


def test_get_account_stmt_callable() -> None:
    """getAccountStmt() callable smoke."""
    from dartlab.providers.edgar.finance.mapper import EdgarMapper

    assert hasattr(EdgarMapper, "getAccountStmt")


def test_get_line_order_callable() -> None:
    """getLineOrder() callable smoke."""
    from dartlab.providers.edgar.finance.mapper import EdgarMapper

    assert hasattr(EdgarMapper, "getLineOrder")


def test_get_primary_stmt_map_callable() -> None:
    """getPrimaryStmtMap() callable smoke."""
    from dartlab.providers.edgar.finance.mapper import EdgarMapper

    assert hasattr(EdgarMapper, "getPrimaryStmtMap")


def test_get_tags_for_snake_ids_callable() -> None:
    """getTagsForSnakeIds() callable smoke."""
    from dartlab.providers.edgar.finance.mapper import EdgarMapper

    assert hasattr(EdgarMapper, "getTagsForSnakeIds")


def test_is_common_tag_callable() -> None:
    """isCommonTag() callable smoke."""
    from dartlab.providers.edgar.finance.mapper import EdgarMapper

    assert hasattr(EdgarMapper, "isCommonTag")


def test_map_callable() -> None:
    """map() callable smoke."""
    from dartlab.providers.edgar.finance.mapper import EdgarMapper

    assert hasattr(EdgarMapper, "map")


def test_map_to_dart_callable() -> None:
    """mapToDart() callable smoke."""
    from dartlab.providers.edgar.finance.mapper import EdgarMapper

    assert hasattr(EdgarMapper, "mapToDart")

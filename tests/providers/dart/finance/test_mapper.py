"""providers/dart/finance/mapper.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.finance.mapper  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_get_callable() -> None:
    """get() callable smoke."""
    from dartlab.providers.dart.finance.mapper import AccountMapper

    assert hasattr(AccountMapper, "get")


def test_label_map_callable() -> None:
    """labelMap() callable smoke."""
    from dartlab.providers.dart.finance.mapper import AccountMapper

    assert hasattr(AccountMapper, "labelMap")


def test_level_map_callable() -> None:
    """levelMap() callable smoke."""
    from dartlab.providers.dart.finance.mapper import AccountMapper

    assert hasattr(AccountMapper, "levelMap")


def test_map_callable() -> None:
    """map() callable smoke."""
    from dartlab.providers.dart.finance.mapper import AccountMapper

    assert hasattr(AccountMapper, "map")


def test_release_callable() -> None:
    """release() callable smoke."""
    from dartlab.providers.dart.finance.mapper import AccountMapper

    assert hasattr(AccountMapper, "release")


def test_sort_order_callable() -> None:
    """sortOrder() callable smoke."""
    from dartlab.providers.dart.finance.mapper import AccountMapper

    assert hasattr(AccountMapper, "sortOrder")

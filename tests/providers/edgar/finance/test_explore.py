"""providers/edgar/finance/explore.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.finance.explore  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_explore_callable() -> None:
    """explore() callable smoke."""
    from dartlab.providers.edgar.finance.explore import explore

    assert callable(explore)


def test_iter_tags_callable() -> None:
    """iterTags() callable smoke."""
    from dartlab.providers.edgar.finance.explore import iterTags

    assert callable(iterTags)


def test_list_tags_callable() -> None:
    """listTags() callable smoke."""
    from dartlab.providers.edgar.finance.explore import listTags

    assert callable(listTags)

"""providers/dart/docs/finance/capitalChange/pipeline.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.capitalChange.pipeline  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_capital_change_callable() -> None:
    """capitalChange() callable smoke."""
    from dartlab.providers.dart.docs.finance.capitalChange.pipeline import capitalChange

    assert callable(capitalChange)

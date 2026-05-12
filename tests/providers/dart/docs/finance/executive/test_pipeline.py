"""providers/dart/docs/finance/executive/pipeline.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.executive.pipeline  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_executive_callable() -> None:
    """executive() callable smoke."""
    from dartlab.providers.dart.docs.finance.executive.pipeline import executive

    assert callable(executive)

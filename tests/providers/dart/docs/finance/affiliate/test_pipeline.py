"""providers/dart/docs/finance/affiliate/pipeline.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.affiliate.pipeline  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_affiliates_callable() -> None:
    """affiliates() callable smoke."""
    from dartlab.providers.dart.docs.finance.affiliate.pipeline import affiliates

    assert callable(affiliates)

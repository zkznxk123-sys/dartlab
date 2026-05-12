"""providers/dart/docs/finance/summary/bridgeMatcher.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.summary.bridgeMatcher  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_name_similarity_callable() -> None:
    """nameSimilarity() callable smoke."""
    from dartlab.providers.dart.docs.finance.summary.bridgeMatcher import nameSimilarity

    assert callable(nameSimilarity)


def test_number_bridge_match_callable() -> None:
    """numberBridgeMatch() callable smoke."""
    from dartlab.providers.dart.docs.finance.summary.bridgeMatcher import numberBridgeMatch

    assert callable(numberBridgeMatch)


def test_period_to_index_callable() -> None:
    """periodToIndex() callable smoke."""
    from dartlab.providers.dart.docs.finance.summary.bridgeMatcher import periodToIndex

    assert callable(periodToIndex)

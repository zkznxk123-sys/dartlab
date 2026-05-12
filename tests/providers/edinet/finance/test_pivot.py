"""providers/edinet/finance/pivot.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edinet.finance.pivot  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")

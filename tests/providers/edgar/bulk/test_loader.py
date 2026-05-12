"""providers/edgar/bulk/loader.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.bulk.loader  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")

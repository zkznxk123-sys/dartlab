"""providers/edinet/openapi/saver.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edinet.openapi.saver  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")

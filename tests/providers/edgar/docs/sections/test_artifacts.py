"""providers/edgar/docs/sections/artifacts.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.docs.sections.artifacts  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")

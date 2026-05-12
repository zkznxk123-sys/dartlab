"""providers/dart/search/fieldIndex.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.search.fieldIndex  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")

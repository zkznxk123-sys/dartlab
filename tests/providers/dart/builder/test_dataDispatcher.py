"""providers/dart/builder/dataDispatcher.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    import dartlab.providers.dart.builder.dataDispatcher  # noqa: F401

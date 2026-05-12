"""providers/dart/builder/filingsCatalog.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    import dartlab.providers.dart.builder.filingsCatalog  # noqa: F401

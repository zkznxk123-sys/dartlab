"""providers/dart/accessor/financeDocAccessor.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    import dartlab.providers.dart.accessor.financeDocAccessor  # noqa: F401

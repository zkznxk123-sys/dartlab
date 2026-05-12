"""providers/dart/accessor/financeAccessor.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    import dartlab.providers.dart.accessor.financeAccessor  # noqa: F401

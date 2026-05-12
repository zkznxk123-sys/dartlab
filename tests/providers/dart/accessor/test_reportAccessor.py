"""providers/dart/accessor/reportAccessor.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    import dartlab.providers.dart.accessor.reportAccessor  # noqa: F401

"""providers/dart/accessor/profileAccessor.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    import dartlab.providers.dart.accessor.profileAccessor  # noqa: F401

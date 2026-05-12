"""providers/dart/accessor/sectionsSource.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    import dartlab.providers.dart.accessor.sectionsSource  # noqa: F401

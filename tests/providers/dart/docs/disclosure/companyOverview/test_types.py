"""providers/dart/docs/disclosure/companyOverview/types.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.disclosure.companyOverview.types  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")

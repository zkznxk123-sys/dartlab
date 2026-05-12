"""providers/dart/openapi/zipCollector.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.openapi.zipCollector  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_collect_callable() -> None:
    """collect() callable smoke."""
    from dartlab.providers.dart.openapi.zipCollector import ZipDocsCollector

    assert hasattr(ZipDocsCollector, "collect")

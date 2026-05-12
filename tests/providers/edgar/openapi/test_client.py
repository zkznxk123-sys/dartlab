"""providers/edgar/openapi/client.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.openapi.client  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_get_json_callable() -> None:
    """getJson() callable smoke."""
    from dartlab.providers.edgar.openapi.client import EdgarClient

    assert hasattr(EdgarClient, "getJson")

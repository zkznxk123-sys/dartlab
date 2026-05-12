"""providers/edgar/openapi/asyncClient.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.openapi.asyncClient  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_close_callable() -> None:
    """close() callable smoke."""
    from dartlab.providers.edgar.openapi.asyncClient import AsyncEdgarClient

    assert hasattr(AsyncEdgarClient, "close")


def test_get_bytes_callable() -> None:
    """getBytes() callable smoke."""
    from dartlab.providers.edgar.openapi.asyncClient import AsyncEdgarClient

    assert hasattr(AsyncEdgarClient, "getBytes")


def test_get_json_callable() -> None:
    """getJson() callable smoke."""
    from dartlab.providers.edgar.openapi.asyncClient import AsyncEdgarClient

    assert hasattr(AsyncEdgarClient, "getJson")

"""providers/dart/openapi/remote.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.gather.dart.remote  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_get_df_callable() -> None:
    """getDf() callable smoke."""
    from dartlab.gather.dart.remote import RemoteDartClient

    assert hasattr(RemoteDartClient, "getDf")


def test_get_df_all_callable() -> None:
    """getDfAll() callable smoke."""
    from dartlab.gather.dart.remote import RemoteDartClient

    assert hasattr(RemoteDartClient, "getDfAll")


def test_get_json_callable() -> None:
    """getJson() callable smoke."""
    from dartlab.gather.dart.remote import RemoteDartClient

    assert hasattr(RemoteDartClient, "getJson")

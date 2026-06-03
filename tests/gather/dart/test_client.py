"""gather/dart/client.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.gather.dart.client  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_get_bytes_callable() -> None:
    """getBytes() callable smoke."""
    from dartlab.gather.dart.client import DartClient

    assert hasattr(DartClient, "getBytes")


def test_get_df_callable() -> None:
    """getDf() callable smoke."""
    from dartlab.gather.dart.client import DartClient

    assert hasattr(DartClient, "getDf")


def test_get_df_all_callable() -> None:
    """getDfAll() callable smoke."""
    from dartlab.gather.dart.client import DartClient

    assert hasattr(DartClient, "getDfAll")


def test_get_json_callable() -> None:
    """getJson() callable smoke."""
    from dartlab.gather.dart.client import DartClient

    assert hasattr(DartClient, "getJson")

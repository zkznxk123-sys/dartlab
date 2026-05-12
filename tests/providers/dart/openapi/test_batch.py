"""providers/dart/openapi/batch.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.openapi.batch  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_close_callable() -> None:
    """close() callable smoke."""
    from dartlab.providers.dart.openapi.batch import AsyncDartClient

    assert hasattr(AsyncDartClient, "close")


def test_get_bytes_callable() -> None:
    """getBytes() callable smoke."""
    from dartlab.providers.dart.openapi.batch import AsyncDartClient

    assert hasattr(AsyncDartClient, "getBytes")


def test_get_df_callable() -> None:
    """getDf() callable smoke."""
    from dartlab.providers.dart.openapi.batch import AsyncDartClient

    assert hasattr(AsyncDartClient, "getDf")


def test_get_json_callable() -> None:
    """getJson() callable smoke."""
    from dartlab.providers.dart.openapi.batch import AsyncDartClient

    assert hasattr(AsyncDartClient, "getJson")


def test_batch_collect_callable() -> None:
    """batchCollect() callable smoke."""
    from dartlab.providers.dart.openapi.batch import batchCollect

    assert callable(batchCollect)


def test_batch_collect_all_callable() -> None:
    """batchCollectAll() callable smoke."""
    from dartlab.providers.dart.openapi.batch import batchCollectAll

    assert callable(batchCollectAll)

"""providers/dart/docs/notes.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.notes  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_all_callable() -> None:
    """all() callable smoke."""
    from dartlab.providers.dart.docs.notes import Notes

    assert hasattr(Notes, "all")


def test_keys_callable() -> None:
    """keys() callable smoke."""
    from dartlab.providers.dart.docs.notes import Notes

    assert hasattr(Notes, "keys")


def test_keys_kr_callable() -> None:
    """keysKr() callable smoke."""
    from dartlab.providers.dart.docs.notes import Notes

    assert hasattr(Notes, "keysKr")


def test_quarterly_callable() -> None:
    """quarterly() callable smoke."""
    from dartlab.providers.dart.docs.notes import Notes

    assert hasattr(Notes, "quarterly")

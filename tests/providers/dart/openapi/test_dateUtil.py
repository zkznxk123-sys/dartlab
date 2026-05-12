"""providers/dart/openapi/dateUtil.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.openapi.dateUtil  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_default_end_callable() -> None:
    """defaultEnd() callable smoke."""
    from dartlab.providers.dart.openapi.dateUtil import defaultEnd

    assert callable(defaultEnd)


def test_default_start_callable() -> None:
    """defaultStart() callable smoke."""
    from dartlab.providers.dart.openapi.dateUtil import defaultStart

    assert callable(defaultStart)


def test_parse_date_callable() -> None:
    """parseDate() callable smoke."""
    from dartlab.providers.dart.openapi.dateUtil import parseDate

    assert callable(parseDate)

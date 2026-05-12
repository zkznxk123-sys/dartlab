"""providers/dart/ops/calendar.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.ops.calendar  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_predict_calendar_callable() -> None:
    """predictCalendar() callable smoke."""
    from dartlab.providers.dart.ops.calendar import predictCalendar

    assert callable(predictCalendar)

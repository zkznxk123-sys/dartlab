"""providers/dart/accessor/reportAccessor.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    import dartlab.providers.dart.accessor.reportAccessor  # noqa: F401


def test_report_frame_inner_callable() -> None:
    """reportFrameInner() callable smoke."""
    from dartlab.providers.dart.accessor.reportAccessor import reportFrameInner

    assert callable(reportFrameInner)


def test_report_pivot_by_se_callable() -> None:
    """reportPivotBySe() callable smoke."""
    from dartlab.providers.dart.accessor.reportAccessor import reportPivotBySe

    assert callable(reportPivotBySe)

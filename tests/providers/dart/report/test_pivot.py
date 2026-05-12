"""providers/dart/report/pivot.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.report.pivot  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_pivot_audit_callable() -> None:
    """pivotAudit() callable smoke."""
    from dartlab.providers.dart.report.pivot import pivotAudit

    assert callable(pivotAudit)


def test_pivot_dividend_callable() -> None:
    """pivotDividend() callable smoke."""
    from dartlab.providers.dart.report.pivot import pivotDividend

    assert callable(pivotDividend)


def test_pivot_employee_callable() -> None:
    """pivotEmployee() callable smoke."""
    from dartlab.providers.dart.report.pivot import pivotEmployee

    assert callable(pivotEmployee)


def test_pivot_executive_callable() -> None:
    """pivotExecutive() callable smoke."""
    from dartlab.providers.dart.report.pivot import pivotExecutive

    assert callable(pivotExecutive)


def test_pivot_major_holder_callable() -> None:
    """pivotMajorHolder() callable smoke."""
    from dartlab.providers.dart.report.pivot import pivotMajorHolder

    assert callable(pivotMajorHolder)

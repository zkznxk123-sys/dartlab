"""providers/edgar/report/employee.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.report.employee  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_extract_employee_callable() -> None:
    """extractEmployee() callable smoke."""
    from dartlab.providers.edgar.report.employee import extractEmployee

    assert callable(extractEmployee)

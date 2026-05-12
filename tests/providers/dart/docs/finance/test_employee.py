"""providers/dart/docs/finance/employee.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.employee  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_employee_callable() -> None:
    """employee() callable smoke."""
    from dartlab.providers.dart.docs.finance.employee import employee

    assert callable(employee)


def test_parse_employee_table_callable() -> None:
    """parseEmployeeTable() callable smoke."""
    from dartlab.providers.dart.docs.finance.employee import parseEmployeeTable

    assert callable(parseEmployeeTable)


def test_parse_tenure_callable() -> None:
    """parseTenure() callable smoke."""
    from dartlab.providers.dart.docs.finance.employee import parseTenure

    assert callable(parseTenure)

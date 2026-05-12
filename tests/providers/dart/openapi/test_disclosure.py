"""providers/dart/openapi/disclosure.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.openapi.disclosure  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_company_info_callable() -> None:
    """companyInfo() callable smoke."""
    from dartlab.providers.dart.openapi.disclosure import companyInfo

    assert callable(companyInfo)


def test_iter_filings_callable() -> None:
    """iterFilings() callable smoke."""
    from dartlab.providers.dart.openapi.disclosure import iterFilings

    assert callable(iterFilings)


def test_list_filings_callable() -> None:
    """listFilings() callable smoke."""
    from dartlab.providers.dart.openapi.disclosure import listFilings

    assert callable(listFilings)

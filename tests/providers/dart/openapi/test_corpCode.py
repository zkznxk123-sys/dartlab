"""providers/dart/openapi/corpCode.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.openapi.corpCode  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_find_corp_code_callable() -> None:
    """findCorpCode() callable smoke."""
    from dartlab.providers.dart.openapi.corpCode import findCorpCode

    assert callable(findCorpCode)


def test_iter_companies_callable() -> None:
    """iterCompanies() callable smoke."""
    from dartlab.providers.dart.openapi.corpCode import iterCompanies

    assert callable(iterCompanies)


def test_load_corp_codes_callable() -> None:
    """loadCorpCodes() callable smoke."""
    from dartlab.providers.dart.openapi.corpCode import loadCorpCodes

    assert callable(loadCorpCodes)


def test_search_companies_callable() -> None:
    """searchCompanies() callable smoke."""
    from dartlab.providers.dart.openapi.corpCode import searchCompanies

    assert callable(searchCompanies)

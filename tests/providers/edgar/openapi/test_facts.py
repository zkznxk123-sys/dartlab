"""providers/edgar/openapi/facts.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.openapi.facts  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_company_facts_to_rows_callable() -> None:
    """companyFactsToRows() callable smoke."""
    from dartlab.providers.edgar.openapi.facts import companyFactsToRows

    assert callable(companyFactsToRows)


def test_get_company_concept_json_callable() -> None:
    """getCompanyConceptJson() callable smoke."""
    from dartlab.providers.edgar.openapi.facts import getCompanyConceptJson

    assert callable(getCompanyConceptJson)


def test_get_company_facts_json_callable() -> None:
    """getCompanyFactsJson() callable smoke."""
    from dartlab.providers.edgar.openapi.facts import getCompanyFactsJson

    assert callable(getCompanyFactsJson)


def test_get_frame_json_callable() -> None:
    """getFrameJson() callable smoke."""
    from dartlab.providers.edgar.openapi.facts import getFrameJson

    assert callable(getFrameJson)

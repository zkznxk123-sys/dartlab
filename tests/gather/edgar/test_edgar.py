"""gather/edgar/edgar.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.gather.edgar.edgar  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_company_callable() -> None:
    """company() callable smoke."""
    from dartlab.gather.edgar.edgar import OpenEdgar

    assert hasattr(OpenEdgar, "company")


def test_company_concept_json_callable() -> None:
    """companyConceptJson() callable smoke."""
    from dartlab.gather.edgar.edgar import OpenEdgar

    assert hasattr(OpenEdgar, "companyConceptJson")


def test_company_facts_json_callable() -> None:
    """companyFactsJson() callable smoke."""
    from dartlab.gather.edgar.edgar import OpenEdgar

    assert hasattr(OpenEdgar, "companyFactsJson")


def test_filings_callable() -> None:
    """filings() callable smoke."""
    from dartlab.gather.edgar.edgar import OpenEdgar

    assert hasattr(OpenEdgar, "filings")


def test_frame_json_callable() -> None:
    """frameJson() callable smoke."""
    from dartlab.gather.edgar.edgar import OpenEdgar

    assert hasattr(OpenEdgar, "frameJson")


def test_search_callable() -> None:
    """search() callable smoke."""
    from dartlab.gather.edgar.edgar import OpenEdgar

    assert hasattr(OpenEdgar, "search")


def test_submissions_json_callable() -> None:
    """submissionsJson() callable smoke."""
    from dartlab.gather.edgar.edgar import OpenEdgar

    assert hasattr(OpenEdgar, "submissionsJson")


def test_info_callable() -> None:
    """info() callable smoke."""
    from dartlab.gather.edgar.edgar import OpenEdgarCompany

    assert hasattr(OpenEdgarCompany, "info")


def test_save_docs_callable() -> None:
    """saveDocs() callable smoke."""
    from dartlab.gather.edgar.edgar import OpenEdgarCompany

    assert hasattr(OpenEdgarCompany, "saveDocs")


def test_save_finance_callable() -> None:
    """saveFinance() callable smoke."""
    from dartlab.gather.edgar.edgar import OpenEdgarCompany

    assert hasattr(OpenEdgarCompany, "saveFinance")

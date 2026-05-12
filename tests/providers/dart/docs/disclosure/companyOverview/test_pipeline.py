"""providers/dart/docs/disclosure/companyOverview/pipeline.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.disclosure.companyOverview.pipeline  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_company_overview_callable() -> None:
    """companyOverview() callable smoke."""
    from dartlab.providers.dart.docs.disclosure.companyOverview.pipeline import companyOverview

    assert callable(companyOverview)

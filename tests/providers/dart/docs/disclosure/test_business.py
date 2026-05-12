"""providers/dart/docs/disclosure/business.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.disclosure.business  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_business_callable() -> None:
    """business() callable smoke."""
    from dartlab.providers.dart.docs.disclosure.business import business

    assert callable(business)


def test_classify_section_callable() -> None:
    """classifySection() callable smoke."""
    from dartlab.providers.dart.docs.disclosure.business import classifySection

    assert callable(classifySection)


def test_compute_changes_callable() -> None:
    """computeChanges() callable smoke."""
    from dartlab.providers.dart.docs.disclosure.business import computeChanges

    assert callable(computeChanges)


def test_extract_from_sub_sections_callable() -> None:
    """extractFromSubSections() callable smoke."""
    from dartlab.providers.dart.docs.disclosure.business import extractFromSubSections

    assert callable(extractFromSubSections)


def test_extract_from_unified_callable() -> None:
    """extractFromUnified() callable smoke."""
    from dartlab.providers.dart.docs.disclosure.business import extractFromUnified

    assert callable(extractFromUnified)


def test_get_business_text_callable() -> None:
    """getBusinessText() callable smoke."""
    from dartlab.providers.dart.docs.disclosure.business import getBusinessText

    assert callable(getBusinessText)


def test_split_by_number_callable() -> None:
    """splitByNumber() callable smoke."""
    from dartlab.providers.dart.docs.disclosure.business import splitByNumber

    assert callable(splitByNumber)

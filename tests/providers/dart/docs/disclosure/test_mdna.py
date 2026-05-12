"""providers/dart/docs/disclosure/mdna.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.disclosure.mdna  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_classify_section_callable() -> None:
    """classifySection() callable smoke."""
    from dartlab.providers.dart.docs.disclosure.mdna import classifySection

    assert callable(classifySection)


def test_extract_overview_callable() -> None:
    """extractOverview() callable smoke."""
    from dartlab.providers.dart.docs.disclosure.mdna import extractOverview

    assert callable(extractOverview)


def test_mdna_callable() -> None:
    """mdna() callable smoke."""
    from dartlab.providers.dart.docs.disclosure.mdna import mdna

    assert callable(mdna)


def test_parse_mdna_callable() -> None:
    """parseMdna() callable smoke."""
    from dartlab.providers.dart.docs.disclosure.mdna import parseMdna

    assert callable(parseMdna)

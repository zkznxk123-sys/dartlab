"""providers/edinet/docs/sections/mapper.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edinet.docs.sections.mapper  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_map_section_title_callable() -> None:
    """mapSectionTitle() callable smoke."""
    from dartlab.providers.edinet.docs.sections.mapper import mapSectionTitle

    assert callable(mapSectionTitle)


def test_normalize_section_title_callable() -> None:
    """normalizeSectionTitle() callable smoke."""
    from dartlab.providers.edinet.docs.sections.mapper import normalizeSectionTitle

    assert callable(normalizeSectionTitle)

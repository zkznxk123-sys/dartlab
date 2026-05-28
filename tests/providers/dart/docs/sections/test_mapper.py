"""providers/dart/docs/sections/mapper.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.sectionsArchive.mapper  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_load_section_mappings_callable() -> None:
    """loadSectionMappings() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.mapper import loadSectionMappings

    assert callable(loadSectionMappings)


def test_map_section_title_callable() -> None:
    """mapSectionTitle() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.mapper import mapSectionTitle

    assert callable(mapSectionTitle)


def test_measure_mapping_rate_callable() -> None:
    """measureMappingRate() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.mapper import measureMappingRate

    assert callable(measureMappingRate)


def test_normalize_section_title_callable() -> None:
    """normalizeSectionTitle() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.mapper import normalizeSectionTitle

    assert callable(normalizeSectionTitle)


def test_strip_section_prefix_callable() -> None:
    """stripSectionPrefix() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.mapper import stripSectionPrefix

    assert callable(stripSectionPrefix)

"""providers/dart/builder/docsSectionsAnalyzer.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    import dartlab.providers.dart.builder.docsSectionsAnalyzer  # noqa: F401


def test_section_topics_callable() -> None:
    """sectionTopics() callable smoke."""
    from dartlab.providers.dart.builder.docsSectionsAnalyzer import SectionsAnalyzer

    assert hasattr(SectionsAnalyzer, "sectionTopics")


def test_sections_coverage_callable() -> None:
    """sectionsCoverage() callable smoke."""
    from dartlab.providers.dart.builder.docsSectionsAnalyzer import SectionsAnalyzer

    assert hasattr(SectionsAnalyzer, "sectionsCoverage")


def test_sections_freq_callable() -> None:
    """sectionsFreq() callable smoke."""
    from dartlab.providers.dart.builder.docsSectionsAnalyzer import SectionsAnalyzer

    assert hasattr(SectionsAnalyzer, "sectionsFreq")


def test_sections_ordered_callable() -> None:
    """sectionsOrdered() callable smoke."""
    from dartlab.providers.dart.builder.docsSectionsAnalyzer import SectionsAnalyzer

    assert hasattr(SectionsAnalyzer, "sectionsOrdered")


def test_sections_semantic_registry_callable() -> None:
    """sectionsSemanticRegistry() callable smoke."""
    from dartlab.providers.dart.builder.docsSectionsAnalyzer import SectionsAnalyzer

    assert hasattr(SectionsAnalyzer, "sectionsSemanticRegistry")


def test_sections_structure_changes_callable() -> None:
    """sectionsStructureChanges() callable smoke."""
    from dartlab.providers.dart.builder.docsSectionsAnalyzer import SectionsAnalyzer

    assert hasattr(SectionsAnalyzer, "sectionsStructureChanges")


def test_sections_structure_events_callable() -> None:
    """sectionsStructureEvents() callable smoke."""
    from dartlab.providers.dart.builder.docsSectionsAnalyzer import SectionsAnalyzer

    assert hasattr(SectionsAnalyzer, "sectionsStructureEvents")


def test_sections_structure_registry_callable() -> None:
    """sectionsStructureRegistry() callable smoke."""
    from dartlab.providers.dart.builder.docsSectionsAnalyzer import SectionsAnalyzer

    assert hasattr(SectionsAnalyzer, "sectionsStructureRegistry")


def test_sections_structure_summary_callable() -> None:
    """sectionsStructureSummary() callable smoke."""
    from dartlab.providers.dart.builder.docsSectionsAnalyzer import SectionsAnalyzer

    assert hasattr(SectionsAnalyzer, "sectionsStructureSummary")


def test_subtopic_long_callable() -> None:
    """subtopicLong() callable smoke."""
    from dartlab.providers.dart.builder.docsSectionsAnalyzer import SectionsAnalyzer

    assert hasattr(SectionsAnalyzer, "subtopicLong")


def test_subtopic_wide_callable() -> None:
    """subtopicWide() callable smoke."""
    from dartlab.providers.dart.builder.docsSectionsAnalyzer import SectionsAnalyzer

    assert hasattr(SectionsAnalyzer, "subtopicWide")


def test_topic_manifest_callable() -> None:
    """topicManifest() callable smoke."""
    from dartlab.providers.dart.builder.docsSectionsAnalyzer import SectionsAnalyzer

    assert hasattr(SectionsAnalyzer, "topicManifest")


def test_topic_outline_callable() -> None:
    """topicOutline() callable smoke."""
    from dartlab.providers.dart.builder.docsSectionsAnalyzer import SectionsAnalyzer

    assert hasattr(SectionsAnalyzer, "topicOutline")


def test_topic_subtables_callable() -> None:
    """topicSubtables() callable smoke."""
    from dartlab.providers.dart.builder.docsSectionsAnalyzer import SectionsAnalyzer

    assert hasattr(SectionsAnalyzer, "topicSubtables")

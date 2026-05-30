"""providers/dart/docs/sections/analysis.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.sections.analysis  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_project_freq_rows_callable() -> None:
    """projectFreqRows() callable smoke."""
    from dartlab.providers.dart.docs.sections.analysis import projectFreqRows

    assert callable(projectFreqRows)


def test_semantic_collisions_callable() -> None:
    """semanticCollisions() callable smoke."""
    from dartlab.providers.dart.docs.sections.analysis import semanticCollisions

    assert callable(semanticCollisions)


def test_semantic_registry_callable() -> None:
    """semanticRegistry() callable smoke."""
    from dartlab.providers.dart.docs.sections.analysis import semanticRegistry

    assert callable(semanticRegistry)


def test_structure_changes_callable() -> None:
    """structureChanges() callable smoke."""
    from dartlab.providers.dart.docs.sections.analysis import structureChanges

    assert callable(structureChanges)


def test_structure_collisions_callable() -> None:
    """structureCollisions() callable smoke."""
    from dartlab.providers.dart.docs.sections.analysis import structureCollisions

    assert callable(structureCollisions)


def test_structure_events_callable() -> None:
    """structureEvents() callable smoke."""
    from dartlab.providers.dart.docs.sections.analysis import structureEvents

    assert callable(structureEvents)


def test_structure_registry_callable() -> None:
    """structureRegistry() callable smoke."""
    from dartlab.providers.dart.docs.sections.analysis import structureRegistry

    assert callable(structureRegistry)


def test_structure_summary_callable() -> None:
    """structureSummary() callable smoke."""
    from dartlab.providers.dart.docs.sections.analysis import structureSummary

    assert callable(structureSummary)

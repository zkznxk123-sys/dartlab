"""providers/dart/docs/sections/artifacts.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.sections.artifacts  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_load_projection_rules_callable() -> None:
    """loadProjectionRules() callable smoke."""
    from dartlab.providers.dart.docs.sections.artifacts import loadProjectionRules

    assert callable(loadProjectionRules)


def test_load_section_profile_table_callable() -> None:
    """loadSectionProfileTable() callable smoke."""
    from dartlab.providers.dart.docs.sections.artifacts import loadSectionProfileTable

    assert callable(loadSectionProfileTable)


def test_packaged_artifact_path_callable() -> None:
    """packagedArtifactPath() callable smoke."""
    from dartlab.providers.dart.docs.sections.artifacts import packagedArtifactPath

    assert callable(packagedArtifactPath)

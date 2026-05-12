"""providers/edgar/docs/sections/artifacts.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.docs.sections.artifacts  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_load_canonical_rows_callable() -> None:
    """loadCanonicalRows() callable smoke."""
    from dartlab.providers.edgar.docs.sections.artifacts import loadCanonicalRows

    assert callable(loadCanonicalRows)


def test_load_coverage_snapshot_callable() -> None:
    """loadCoverageSnapshot() callable smoke."""
    from dartlab.providers.edgar.docs.sections.artifacts import loadCoverageSnapshot

    assert callable(loadCoverageSnapshot)


def test_load_topic_drafts_callable() -> None:
    """loadTopicDrafts() callable smoke."""
    from dartlab.providers.edgar.docs.sections.artifacts import loadTopicDrafts

    assert callable(loadTopicDrafts)


def test_packaged_artifact_path_callable() -> None:
    """packagedArtifactPath() callable smoke."""
    from dartlab.providers.edgar.docs.sections.artifacts import packagedArtifactPath

    assert callable(packagedArtifactPath)

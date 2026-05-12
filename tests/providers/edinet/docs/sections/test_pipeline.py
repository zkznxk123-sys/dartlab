"""providers/edinet/docs/sections/pipeline.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edinet.docs.sections.pipeline  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_build_sections_callable() -> None:
    """buildSections() callable smoke."""
    from dartlab.providers.edinet.docs.sections.pipeline import buildSections

    assert callable(buildSections)

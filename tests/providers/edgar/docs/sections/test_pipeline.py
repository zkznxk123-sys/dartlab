"""providers/edgar/docs/sections/pipeline.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.docs.sections.pipeline  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_sections_callable() -> None:
    """sections() callable smoke."""
    from dartlab.providers.edgar.docs.sections.pipeline import sections

    assert callable(sections)

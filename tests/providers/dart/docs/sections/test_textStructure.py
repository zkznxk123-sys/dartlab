"""providers/dart/docs/sections/textStructure.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.sectionsArchive.textStructure  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_parse_text_structure_callable() -> None:
    """parseTextStructure() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.textStructure import parseTextStructure

    assert callable(parseTextStructure)


def test_parse_text_structure_with_state_callable() -> None:
    """parseTextStructureWithState() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.textStructure import parseTextStructureWithState

    assert callable(parseTextStructureWithState)

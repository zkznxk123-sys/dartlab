"""providers/edgar/docs/notesParsers.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.docs.notesParsers  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_available_categories_callable() -> None:
    """availableCategories() callable smoke."""
    from dartlab.providers.edgar.docs.notesParsers import availableCategories

    assert callable(availableCategories)


def test_extract_all_note_categories_callable() -> None:
    """extractAllNoteCategories() callable smoke."""
    from dartlab.providers.edgar.docs.notesParsers import extractAllNoteCategories

    assert callable(extractAllNoteCategories)


def test_extract_note_category_callable() -> None:
    """extractNoteCategory() callable smoke."""
    from dartlab.providers.edgar.docs.notesParsers import extractNoteCategory

    assert callable(extractNoteCategory)

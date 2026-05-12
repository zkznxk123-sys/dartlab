"""providers/edgar/docs/notes.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.docs.notes  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_note_categories_callable() -> None:
    """noteCategories() callable smoke."""
    from dartlab.providers.edgar.docs.notes import noteCategories

    assert callable(noteCategories)


def test_notes_callable() -> None:
    """notes() callable smoke."""
    from dartlab.providers.edgar.docs.notes import notes

    assert callable(notes)


def test_notes_by_category_callable() -> None:
    """notesByCategory() callable smoke."""
    from dartlab.providers.edgar.docs.notes import notesByCategory

    assert callable(notesByCategory)

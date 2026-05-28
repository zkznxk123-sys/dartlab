"""providers/dart/docs/sections/types.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.sectionsArchive.types  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_compare_callable() -> None:
    """compare() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.types import SectionResult

    assert hasattr(SectionResult, "compare")


def test_diff_callable() -> None:
    """diff() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.types import SectionResult

    assert hasattr(SectionResult, "diff")


def test_overview_callable() -> None:
    """overview() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.types import SectionResult

    assert hasattr(SectionResult, "overview")


def test_search_callable() -> None:
    """search() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.types import SectionResult

    assert hasattr(SectionResult, "search")


def test_by_kind_callable() -> None:
    """byKind() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.types import YearSections

    assert hasattr(YearSections, "byKind")


def test_by_major_callable() -> None:
    """byMajor() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.types import YearSections

    assert hasattr(YearSections, "byMajor")


def test_text_chunks_callable() -> None:
    """textChunks() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.types import YearSections

    assert hasattr(YearSections, "textChunks")


def test_to_leaf_map_callable() -> None:
    """toLeafMap() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.types import YearSections

    assert hasattr(YearSections, "toLeafMap")


def test_to_lines_df_callable() -> None:
    """toLinesDf() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.types import YearSections

    assert hasattr(YearSections, "toLinesDf")

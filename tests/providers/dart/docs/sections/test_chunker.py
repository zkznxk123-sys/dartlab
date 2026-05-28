"""providers/dart/docs/sections/chunker.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.sectionsLegacy.chunker  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_chunk_rows_callable() -> None:
    """chunkRows() callable smoke."""
    from dartlab.providers.dart.docs.sectionsLegacy.chunker import chunkRows

    assert callable(chunkRows)


def test_chunk_section_callable() -> None:
    """chunkSection() callable smoke."""
    from dartlab.providers.dart.docs.sectionsLegacy.chunker import chunkSection

    assert callable(chunkSection)


def test_parse_major_num_callable() -> None:
    """parseMajorNum() callable smoke."""
    from dartlab.providers.dart.docs.sectionsLegacy.chunker import parseMajorNum

    assert callable(parseMajorNum)


def test_parse_sub_num_callable() -> None:
    """parseSubNum() callable smoke."""
    from dartlab.providers.dart.docs.sectionsLegacy.chunker import parseSubNum

    assert callable(parseSubNum)


def test_separate_table_and_text_callable() -> None:
    """separateTableAndText() callable smoke."""
    from dartlab.providers.dart.docs.sectionsLegacy.chunker import separateTableAndText

    assert callable(separateTableAndText)


def test_split_by_headings_callable() -> None:
    """splitByHeadings() callable smoke."""
    from dartlab.providers.dart.docs.sectionsLegacy.chunker import splitByHeadings

    assert callable(splitByHeadings)

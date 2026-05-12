"""providers/dart/docs/finance/boardOfDirectors/parser.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.boardOfDirectors.parser  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_classify_block_callable() -> None:
    """classifyBlock() callable smoke."""
    from dartlab.providers.dart.docs.finance.boardOfDirectors.parser import classifyBlock

    assert callable(classifyBlock)


def test_extract_table_blocks_callable() -> None:
    """extractTableBlocks() callable smoke."""
    from dartlab.providers.dart.docs.finance.boardOfDirectors.parser import extractTableBlocks

    assert callable(extractTableBlocks)


def test_parse_board_meeting_callable() -> None:
    """parseBoardMeeting() callable smoke."""
    from dartlab.providers.dart.docs.finance.boardOfDirectors.parser import parseBoardMeeting

    assert callable(parseBoardMeeting)


def test_parse_committee_callable() -> None:
    """parseCommittee() callable smoke."""
    from dartlab.providers.dart.docs.finance.boardOfDirectors.parser import parseCommittee

    assert callable(parseCommittee)


def test_parse_director_count_callable() -> None:
    """parseDirectorCount() callable smoke."""
    from dartlab.providers.dart.docs.finance.boardOfDirectors.parser import parseDirectorCount

    assert callable(parseDirectorCount)


def test_parse_director_count_from_text_callable() -> None:
    """parseDirectorCountFromText() callable smoke."""
    from dartlab.providers.dart.docs.finance.boardOfDirectors.parser import parseDirectorCountFromText

    assert callable(parseDirectorCountFromText)

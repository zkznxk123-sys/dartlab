"""providers/dart/docs/finance/shareholderMeeting.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.shareholderMeeting  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_is_separator_row_callable() -> None:
    """isSeparatorRow() callable smoke."""
    from dartlab.providers.dart.docs.finance.shareholderMeeting import isSeparatorRow

    assert callable(isSeparatorRow)


def test_parse_amount_callable() -> None:
    """parseAmount() callable smoke."""
    from dartlab.providers.dart.docs.finance.shareholderMeeting import parseAmount

    assert callable(parseAmount)


def test_parse_meeting_agenda_callable() -> None:
    """parseMeetingAgenda() callable smoke."""
    from dartlab.providers.dart.docs.finance.shareholderMeeting import parseMeetingAgenda

    assert callable(parseMeetingAgenda)


def test_shareholder_meeting_callable() -> None:
    """shareholderMeeting() callable smoke."""
    from dartlab.providers.dart.docs.finance.shareholderMeeting import shareholderMeeting

    assert callable(shareholderMeeting)


def test_split_cells_callable() -> None:
    """splitCells() callable smoke."""
    from dartlab.providers.dart.docs.finance.shareholderMeeting import splitCells

    assert callable(splitCells)

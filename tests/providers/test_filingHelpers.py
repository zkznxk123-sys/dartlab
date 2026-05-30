"""providers/filingHelpers.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers._common.filingHelpers  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_coerce_date_callable() -> None:
    """coerceDate() callable smoke."""
    from dartlab.providers._common.filingHelpers import coerceDate

    assert callable(coerceDate)


def test_filing_record_callable() -> None:
    """filingRecord() callable smoke."""
    from dartlab.providers._common.filingHelpers import filingRecord

    assert callable(filingRecord)


def test_filter_filings_by_keyword_callable() -> None:
    """filterFilingsByKeyword() callable smoke."""
    from dartlab.providers._common.filingHelpers import filterFilingsByKeyword

    assert callable(filterFilingsByKeyword)


def test_resolve_date_window_callable() -> None:
    """resolveDateWindow() callable smoke."""
    from dartlab.providers._common.filingHelpers import resolveDateWindow

    assert callable(resolveDateWindow)


def test_split_keywords_callable() -> None:
    """splitKeywords() callable smoke."""
    from dartlab.providers._common.filingHelpers import splitKeywords

    assert callable(splitKeywords)


def test_truncate_text_callable() -> None:
    """truncateText() callable smoke."""
    from dartlab.providers._common.filingHelpers import truncateText

    assert callable(truncateText)

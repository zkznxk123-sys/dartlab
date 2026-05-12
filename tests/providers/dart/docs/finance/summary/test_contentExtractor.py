"""providers/dart/docs/finance/summary/contentExtractor.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.summary.contentExtractor  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_extract_summary_content_callable() -> None:
    """extractSummaryContent() callable smoke."""
    from dartlab.providers.dart.docs.finance.summary.contentExtractor import extractSummaryContent

    assert callable(extractSummaryContent)

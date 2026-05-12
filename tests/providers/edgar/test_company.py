"""providers/edgar/company.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.company  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_ask_callable() -> None:
    """ask() callable smoke."""
    from dartlab.providers.edgar.company import Company

    assert hasattr(Company, "ask")


def test_audit_callable() -> None:
    """audit() callable smoke."""
    from dartlab.providers.edgar.company import Company

    assert hasattr(Company, "audit")


def test_calendar_callable() -> None:
    """calendar() callable smoke."""
    from dartlab.providers.edgar.company import Company

    assert hasattr(Company, "calendar")


def test_can_handle_callable() -> None:
    """canHandle() callable smoke."""
    from dartlab.providers.edgar.company import Company

    assert hasattr(Company, "canHandle")


def test_capital_callable() -> None:
    """capital() callable smoke."""
    from dartlab.providers.edgar.company import Company

    assert hasattr(Company, "capital")


def test_causal_weights_callable() -> None:
    """causalWeights() callable smoke."""
    from dartlab.providers.edgar.company import Company

    assert hasattr(Company, "causalWeights")


def test_cleanup_cache_callable() -> None:
    """cleanupCache() callable smoke."""
    from dartlab.providers.edgar.company import Company

    assert hasattr(Company, "cleanupCache")


def test_debt_callable() -> None:
    """debt() callable smoke."""
    from dartlab.providers.edgar.company import Company

    assert hasattr(Company, "debt")


def test_diff_callable() -> None:
    """diff() callable smoke."""
    from dartlab.providers.edgar.company import Company

    assert hasattr(Company, "diff")


def test_disclosure_callable() -> None:
    """disclosure() callable smoke."""
    from dartlab.providers.edgar.company import Company

    assert hasattr(Company, "disclosure")


def test_filings_callable() -> None:
    """filings() callable smoke."""
    from dartlab.providers.edgar.company import Company

    assert hasattr(Company, "filings")


def test_gather_callable() -> None:
    """gather() callable smoke."""
    from dartlab.providers.edgar.company import Company

    assert hasattr(Company, "gather")


def test_governance_callable() -> None:
    """governance() callable smoke."""
    from dartlab.providers.edgar.company import Company

    assert hasattr(Company, "governance")


def test_keyword_trend_callable() -> None:
    """keywordTrend() callable smoke."""
    from dartlab.providers.edgar.company import Company

    assert hasattr(Company, "keywordTrend")


def test_listing_callable() -> None:
    """listing() callable smoke."""
    from dartlab.providers.edgar.company import Company

    assert hasattr(Company, "listing")


def test_live_filings_callable() -> None:
    """liveFilings() callable smoke."""
    from dartlab.providers.edgar.company import Company

    assert hasattr(Company, "liveFilings")


def test_macro_callable() -> None:
    """macro() callable smoke."""
    from dartlab.providers.edgar.company import Company

    assert hasattr(Company, "macro")


def test_memory_snapshot_callable() -> None:
    """memorySnapshot() callable smoke."""
    from dartlab.providers.edgar.company import Company

    assert hasattr(Company, "memorySnapshot")


def test_narrative_diff_callable() -> None:
    """narrativeDiff() callable smoke."""
    from dartlab.providers.edgar.company import Company

    assert hasattr(Company, "narrativeDiff")


def test_news_callable() -> None:
    """news() callable smoke."""
    from dartlab.providers.edgar.company import Company

    assert hasattr(Company, "news")


def test_priority_callable() -> None:
    """priority() callable smoke."""
    from dartlab.providers.edgar.company import Company

    assert hasattr(Company, "priority")


def test_read_filing_callable() -> None:
    """readFiling() callable smoke."""
    from dartlab.providers.edgar.company import Company

    assert hasattr(Company, "readFiling")


def test_refresh_from_api_callable() -> None:
    """refreshFromApi() callable smoke."""
    from dartlab.providers.edgar.company import Company

    assert hasattr(Company, "refreshFromApi")


def test_search_callable() -> None:
    """search() callable smoke."""
    from dartlab.providers.edgar.company import Company

    assert hasattr(Company, "search")


def test_story_tree_callable() -> None:
    """storyTree() callable smoke."""
    from dartlab.providers.edgar.company import Company

    assert hasattr(Company, "storyTree")


def test_table_callable() -> None:
    """table() callable smoke."""
    from dartlab.providers.edgar.company import Company

    assert hasattr(Company, "table")


def test_trace_callable() -> None:
    """trace() callable smoke."""
    from dartlab.providers.edgar.company import Company

    assert hasattr(Company, "trace")


def test_validate_story_callable() -> None:
    """validateStory() callable smoke."""
    from dartlab.providers.edgar.company import Company

    assert hasattr(Company, "validateStory")


def test_valuation_impact_callable() -> None:
    """valuationImpact() callable smoke."""
    from dartlab.providers.edgar.company import Company

    assert hasattr(Company, "valuationImpact")


def test_view_callable() -> None:
    """view() callable smoke."""
    from dartlab.providers.edgar.company import Company

    assert hasattr(Company, "view")


def test_watch_callable() -> None:
    """watch() callable smoke."""
    from dartlab.providers.edgar.company import Company

    assert hasattr(Company, "watch")


def test_workforce_callable() -> None:
    """workforce() callable smoke."""
    from dartlab.providers.edgar.company import Company

    assert hasattr(Company, "workforce")

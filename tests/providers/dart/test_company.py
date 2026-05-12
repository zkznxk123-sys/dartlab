"""providers/dart/company.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.company  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_ask_callable() -> None:
    """ask() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "ask")


def test_audit_callable() -> None:
    """audit() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "audit")


def test_calendar_callable() -> None:
    """calendar() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "calendar")


def test_can_handle_callable() -> None:
    """canHandle() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "canHandle")


def test_capital_callable() -> None:
    """capital() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "capital")


def test_causal_weights_callable() -> None:
    """causalWeights() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "causalWeights")


def test_cleanup_cache_callable() -> None:
    """cleanupCache() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "cleanupCache")


def test_code_name_callable() -> None:
    """codeName() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "codeName")


def test_debt_callable() -> None:
    """debt() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "debt")


def test_diff_callable() -> None:
    """diff() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "diff")


def test_disclosure_callable() -> None:
    """disclosure() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "disclosure")


def test_filings_callable() -> None:
    """filings() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "filings")


def test_gather_callable() -> None:
    """gather() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "gather")


def test_governance_callable() -> None:
    """governance() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "governance")


def test_industry_callable() -> None:
    """industry() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "industry")


def test_keyword_trend_callable() -> None:
    """keywordTrend() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "keywordTrend")


def test_listing_callable() -> None:
    """listing() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "listing")


def test_live_filings_callable() -> None:
    """liveFilings() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "liveFilings")


def test_macro_callable() -> None:
    """macro() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "macro")


def test_memory_snapshot_callable() -> None:
    """memorySnapshot() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "memorySnapshot")


def test_narrative_diff_callable() -> None:
    """narrativeDiff() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "narrativeDiff")


def test_network_callable() -> None:
    """network() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "network")


def test_news_callable() -> None:
    """news() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "news")


def test_priority_callable() -> None:
    """priority() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "priority")


def test_read_filing_callable() -> None:
    """readFiling() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "readFiling")


def test_resolve_callable() -> None:
    """resolve() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "resolve")


def test_search_callable() -> None:
    """search() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "search")


def test_status_callable() -> None:
    """status() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "status")


def test_story_tree_callable() -> None:
    """storyTree() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "storyTree")


def test_table_callable() -> None:
    """table() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "table")


def test_topic_summaries_callable() -> None:
    """topicSummaries() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "topicSummaries")


def test_trace_callable() -> None:
    """trace() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "trace")


def test_update_callable() -> None:
    """update() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "update")


def test_validate_story_callable() -> None:
    """validateStory() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "validateStory")


def test_valuation_impact_callable() -> None:
    """valuationImpact() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "valuationImpact")


def test_view_callable() -> None:
    """view() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "view")


def test_watch_callable() -> None:
    """watch() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "watch")


def test_workforce_callable() -> None:
    """workforce() callable smoke."""
    from dartlab.providers.dart.company import Company

    assert hasattr(Company, "workforce")


def test_code_to_name_callable() -> None:
    """codeToName() callable smoke."""
    from dartlab.providers.dart.company import codeToName

    assert callable(codeToName)


def test_get_kind_list_callable() -> None:
    """getKindList() callable smoke."""
    from dartlab.providers.dart.company import getKindList

    assert callable(getKindList)


def test_iter_export_modules_callable() -> None:
    """iterExportModules() callable smoke."""
    from dartlab.providers.dart.company import iterExportModules

    assert callable(iterExportModules)


def test_iter_name_callable() -> None:
    """iterName() callable smoke."""
    from dartlab.providers.dart.company import iterName

    assert callable(iterName)


def test_list_export_modules_callable() -> None:
    """listExportModules() callable smoke."""
    from dartlab.providers.dart.company import listExportModules

    assert callable(listExportModules)


def test_name_to_code_callable() -> None:
    """nameToCode() callable smoke."""
    from dartlab.providers.dart.company import nameToCode

    assert callable(nameToCode)


def test_rebuild_module_registry_callable() -> None:
    """rebuildModuleRegistry() callable smoke."""
    from dartlab.providers.dart.company import rebuildModuleRegistry

    assert callable(rebuildModuleRegistry)


def test_search_name_callable() -> None:
    """searchName() callable smoke."""
    from dartlab.providers.dart.company import searchName

    assert callable(searchName)

"""providers/dart/search/api.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.search.api  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_build_index_callable() -> None:
    """buildIndex() callable smoke."""
    from dartlab.providers.dart.search.api import buildIndex

    assert callable(buildIndex)


def test_collect_meta_callable() -> None:
    """collectMeta() callable smoke."""
    from dartlab.providers.dart.search.api import collectMeta

    assert callable(collectMeta)


def test_dna_callable() -> None:
    """dna() callable smoke."""
    from dartlab.providers.dart.search.api import dna

    assert callable(dna)


def test_fill_content_callable() -> None:
    """fillContent() callable smoke."""
    from dartlab.providers.dart.search.api import fillContent

    assert callable(fillContent)


def test_profile_callable() -> None:
    """profile() callable smoke."""
    from dartlab.providers.dart.search.api import profile

    assert callable(profile)


def test_pull_index_callable() -> None:
    """pullIndex() callable smoke."""
    from dartlab.providers.dart.search.api import pullIndex

    assert callable(pullIndex)


def test_pulse_callable() -> None:
    """pulse() callable smoke."""
    from dartlab.providers.dart.search.api import pulse

    assert callable(pulse)


def test_push_index_callable() -> None:
    """pushIndex() callable smoke."""
    from dartlab.providers.dart.search.api import pushIndex

    assert callable(pushIndex)


def test_rebuild_content_callable() -> None:
    """rebuildContent() callable smoke."""
    from dartlab.providers.dart.search.api import rebuildContent

    assert callable(rebuildContent)


def test_rebuild_content_delta_callable() -> None:
    """rebuildContentDelta() callable smoke."""
    from dartlab.providers.dart.search.api import rebuildContentDelta

    assert callable(rebuildContentDelta)


def test_rebuild_index_callable() -> None:
    """rebuildIndex() callable smoke."""
    from dartlab.providers.dart.search.api import rebuildIndex

    assert callable(rebuildIndex)


def test_search_callable() -> None:
    """search() callable smoke."""
    from dartlab.providers.dart.search.api import search

    assert callable(search)


def test_search_accepts_top_k_alias(monkeypatch) -> None:
    """provider search 도 topK 를 limit 호환 alias 로 받는다."""
    import polars as pl

    from dartlab.providers.dart.search import api

    calls = {}

    def fakeSearchAuto(query, *, corpCode, stockCode, sourceKind=None, limit=10):
        calls.update(
            {
                "query": query,
                "corpCode": corpCode,
                "stockCode": stockCode,
                "sourceKind": sourceKind,
                "limit": limit,
            }
        )
        return pl.DataFrame({"info": ["ok"]})

    monkeypatch.setattr(api, "_searchAuto", fakeSearchAuto)

    result = api.search("유상증자", topK=4)

    assert result["info"].to_list() == ["ok"]
    assert calls["limit"] == 4


def test_search_records_raw_query_log_when_enabled(monkeypatch, tmp_path) -> None:
    import json

    import polars as pl

    from dartlab.providers.dart.search import api

    out = tmp_path / "queryLogRaw.jsonl"
    monkeypatch.setenv("DARTLAB_SEARCH_QUERY_LOG", str(out))

    def fakeSearchAuto(query, *, corpCode, stockCode, sourceKind=None, limit=10):
        return pl.DataFrame({"info": ["ok"]})

    monkeypatch.setattr(api, "_searchAuto", fakeSearchAuto)

    api.search("유상증자", topK=2)

    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["query"] == "유상증자"
    assert rows[0]["goldOrigin"] == "userLog"
    assert rows[0]["reviewStatus"] == "candidate"
    assert rows[0]["params"]["limit"] == 2


def test_resolve_corp_accepts_company_name_with_name_to_code(monkeypatch) -> None:
    from dartlab.providers.dart.search import api

    class FakeResolver:
        def nameToCode(self, name: str) -> str | None:
            return {"삼성전자": "005930"}.get(name)

        def search(self, query: str):
            raise AssertionError("nameToCode should resolve exact company names first")

    import dartlab.core.listingResolver as listingResolver

    monkeypatch.setattr(listingResolver, "getListingResolver", lambda: FakeResolver())

    assert api._resolveCorp("삼성전자") == (None, "005930")


def test_similar_companies_callable() -> None:
    """similarCompanies() callable smoke."""
    from dartlab.providers.dart.search.api import similarCompanies

    assert callable(similarCompanies)


def test_stats_callable() -> None:
    """stats() callable smoke."""
    from dartlab.providers.dart.search.api import stats

    assert callable(stats)


def test_timeline_callable() -> None:
    """timeline() callable smoke."""
    from dartlab.providers.dart.search.api import timeline

    assert callable(timeline)

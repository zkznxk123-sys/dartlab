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
    assert calls["limit"] == 50


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


def test_auto_search_prefers_title_lane_for_disclosure_event(monkeypatch) -> None:
    import polars as pl

    import dartlab.providers.dart.search.unified as unified
    from dartlab.providers.dart.search import api

    def fakeTitle(query, *, corpCode, stockCode, limit):
        return pl.DataFrame(
            {
                "rcept_no": ["title-hit"],
                "section_order": [0],
                "sourceRef": ["dart:allFilings:title-hit#section=0"],
                "report_nm": ["주요사항보고서(무상증자결정)"],
                "score": [10.0],
            }
        )

    def fakeContent(query, *, corpCode, stockCode, sourceKind=None, limit):
        return pl.DataFrame(
            {
                "rcept_no": ["content-hit"],
                "section_order": [0],
                "sourceRef": ["dart:allFilings:content-hit#section=0"],
                "report_nm": ["증권발행결과"],
                "score": [0.03],
            }
        )

    monkeypatch.setattr(api, "_searchTitle", fakeTitle)
    monkeypatch.setattr(unified, "searchUnified", fakeContent)

    result = api._searchAuto("무상증자 결정 공시", corpCode=None, stockCode=None, sourceKind="filing", limit=2)

    assert result["rcept_no"].to_list() == ["title-hit", "content-hit"]
    assert result["scope"].to_list() == ["title", "content"]


def test_auto_search_keeps_content_lane_for_body_semantic_query(monkeypatch) -> None:
    import polars as pl

    import dartlab.providers.dart.search.unified as unified
    from dartlab.providers.dart.search import api

    def fakeTitle(query, *, corpCode, stockCode, limit):
        raise AssertionError("body semantic query should not call title lane")

    def fakeContent(query, *, corpCode, stockCode, sourceKind=None, limit):
        return pl.DataFrame({"rcept_no": ["content-hit"], "score": [0.2]})

    monkeypatch.setattr(api, "_searchTitle", fakeTitle)
    monkeypatch.setattr(unified, "searchUnified", fakeContent)

    result = api._searchAuto("환율 리스크 사업보고서 본문", corpCode=None, stockCode=None, sourceKind="filing", limit=1)

    assert result["rcept_no"].to_list() == ["content-hit"]
    assert result["scope"].to_list() == ["auto"]


def test_auto_search_keeps_content_lane_for_topic_original_filing_query(monkeypatch) -> None:
    import polars as pl

    import dartlab.providers.dart.search.unified as unified
    from dartlab.providers.dart.search import api

    def fakeTitle(query, *, corpCode, stockCode, limit):
        raise AssertionError("topic original-filing query should not call title lane")

    def fakeContent(query, *, corpCode, stockCode, sourceKind=None, limit):
        return pl.DataFrame({"rcept_no": ["hbm-body-hit"], "score": [4.2]})

    monkeypatch.setattr(api, "_searchTitle", fakeTitle)
    monkeypatch.setattr(unified, "searchUnified", fakeContent)

    result = api._searchAuto(
        "HBM 설비투자와 TC bonder 증설을 언급한 공시 원문",
        corpCode=None,
        stockCode=None,
        sourceKind="filing",
        limit=1,
    )

    assert result["rcept_no"].to_list() == ["hbm-body-hit"]
    assert result["scope"].to_list() == ["auto"]


def test_retrieval_limit_widens_internal_candidate_pool() -> None:
    from dartlab.providers.dart.search import api

    assert api._retrievalLimit("환율 리스크 사업보고서 본문", 10, sourceKind="filing") == 50
    assert api._retrievalLimit("대표이사 변경", 30, sourceKind="filing") == 100


def test_rank_answerable_first_preserves_answerable_order() -> None:
    import polars as pl

    from dartlab.providers.dart.search import api

    result = api._rankAnswerableFirst(
        pl.DataFrame({"id": [1, 2, 3], "answerable": [False, True, True]}),
        limit=3,
    )

    assert result["id"].to_list() == [2, 3, 1]


def test_mark_low_confidence_rows_marks_answerable_false() -> None:
    import polars as pl

    from dartlab.providers.dart.search.answerability import markLowConfidenceRows

    result = markLowConfidenceRows(
        pl.DataFrame(
            {
                "id": [1, 2],
                "score": [0.016, 0.01],
                "answerable": [True, True],
                "notAnswerableReason": ["", ""],
            }
        )
    )

    assert result["answerable"].to_list() == [False, False]
    assert result["notAnswerableReason"].to_list() == ["lowConfidence", "lowConfidence"]


def test_mark_low_confidence_rows_keeps_high_confidence_pool() -> None:
    import polars as pl

    from dartlab.providers.dart.search.answerability import markLowConfidenceRows

    result = markLowConfidenceRows(
        pl.DataFrame(
            {
                "id": [1, 2],
                "score": [0.03, 0.01],
                "answerable": [True, True],
                "notAnswerableReason": ["", ""],
            }
        )
    )

    assert result["answerable"].to_list() == [True, True]


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

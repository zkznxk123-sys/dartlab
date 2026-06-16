"""providers/dart/search/answerability.py mirror tests."""

from __future__ import annotations

import polars as pl


def test_apply_answerability_import_and_empty() -> None:
    from dartlab.providers.dart.search.answerability import applyAnswerability

    assert applyAnswerability(pl.DataFrame()).height == 0


def test_apply_answerability_marks_stale_source_for_fresh_query() -> None:
    from dartlab.providers.dart.search.answerability import applyAnswerability
    from dartlab.providers.dart.search.facetPlanner import QueryFacets

    df = pl.DataFrame(
        [
            {
                "source": "allFilings",
                "sourceRef": "dart:allFilings:20260501000001#section=0",
                "snippet": "오래된 공시",
                "dataAsOf": "20260501",
            },
            {
                "source": "news",
                "sourceRef": "news:fresh",
                "snippet": "최신 뉴스",
                "dataAsOf": "20260614",
            },
        ]
    )
    out = applyAnswerability(df, facets=QueryFacets(freshnessRequired=True), today="20260615")
    bySource = {row["source"]: row for row in out.iter_rows(named=True)}
    assert bySource["allFilings"]["answerable"] is False
    assert bySource["allFilings"]["notAnswerableReason"] == "staleSource"
    assert bySource["news"]["answerable"] is True


def test_apply_answerability_accepts_matching_stock_code_when_company_name_missing() -> None:
    from dartlab.providers.dart.search.answerability import applyAnswerability
    from dartlab.providers.dart.search.facetPlanner import QueryFacets

    df = pl.DataFrame(
        [
            {
                "source": "panel",
                "sourceRef": "dart:panel:20260615000001#section=0",
                "snippet": "대표이사 변경",
                "dataAsOf": "20260615",
                "stock_code": "005930",
                "corp_name": "",
            }
        ]
    )

    out = applyAnswerability(df, facets=QueryFacets(stockCode="005930", companyName="삼성전자"))

    assert out.row(0, named=True)["answerable"] is True


def test_apply_answerability_matches_report_facet_from_evidence_text_when_metadata_missing() -> None:
    from dartlab.providers.dart.search.answerability import applyAnswerability
    from dartlab.providers.dart.search.facetPlanner import QueryFacets

    df = pl.DataFrame(
        [
            {
                "source": "panel",
                "sourceRef": "dart:panel:20260615000001#section=0",
                "report_nm": "",
                "section_title": "0",
                "snippet": "사업보고서 본문에는 이사의 보수와 사업의 내용이 포함된다.",
                "dataAsOf": "20260615",
            }
        ]
    )

    out = applyAnswerability(df, facets=QueryFacets(reportTerms=("사업보고서",)))

    assert out.row(0, named=True)["answerable"] is True

"""providers/dart/search/facetPlanner.py mirror tests."""

from __future__ import annotations


def test_plan_query_facets_extracts_receipt_and_report() -> None:
    from dartlab.providers.dart.search.facetPlanner import planQueryFacets

    facets = planQueryFacets("20260615000001 사업보고서")
    assert facets.receiptNumbers == ("20260615000001",)
    assert facets.reportTerms == ("사업보고서",)


def test_plan_query_facets_detects_freshness_intent() -> None:
    from dartlab.providers.dart.search.facetPlanner import planQueryFacets

    assert planQueryFacets("최신 유상증자 공시").freshnessRequired is True
    assert planQueryFacets("latest semiconductor news").freshnessRequired is True


def test_plan_query_facets_extracts_year_and_literal_constraints() -> None:
    from dartlab.providers.dart.search.facetPlanner import planQueryFacets

    facets = planQueryFacets("zzqwvxnotlistedalpha999 2099년 합병 공시")

    assert facets.years == ("2099",)
    assert facets.literalTerms == ("zzqwvxnotlistedalpha999",)


def test_plan_query_facets_extracts_company_name_from_query(monkeypatch) -> None:
    from dartlab.providers.dart.search.facetPlanner import planQueryFacets

    class FakeResolver:
        def nameToCode(self, name: str) -> str | None:
            return {"삼성전자": "005930"}.get(name)

    import dartlab.core.listingResolver as listingResolver

    monkeypatch.setattr(listingResolver, "getListingResolver", lambda: FakeResolver())

    facets = planQueryFacets("삼성전자 대표이사 변경")

    assert facets.companyName == "삼성전자"
    assert facets.stockCode == "005930"

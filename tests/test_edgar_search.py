"""EDGAR 검색 경로 회귀 가드 (Phase 11 A1~A3)."""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_edgar_search_intel_by_ticker():
    """INTC ticker 로 Intel Corp 매칭."""
    from dartlab.providers.edgar.company import Company as EdgarCompany

    r = EdgarCompany.search("INTC")
    assert r.height > 0
    assert "INTC" in r["종목코드"].to_list()


@pytest.mark.unit
def test_edgar_search_intel_by_name():
    """'Intel' 회사명 검색."""
    from dartlab.providers.edgar.company import Company as EdgarCompany

    r = EdgarCompany.search("Intel")
    assert r.height > 0
    names = r["회사명"].to_list()
    assert any("INTEL" in n.upper() for n in names)


@pytest.mark.unit
def test_edgar_listing_returns_dataframe():
    """listing 이 상장 기업 DataFrame 반환."""
    from dartlab.providers.edgar.company import Company as EdgarCompany

    df = EdgarCompany.listing()
    assert df.height > 1000  # 수천 개 상장사
    assert set(df.columns) >= {"종목코드", "회사명", "시장구분", "cik"}


@pytest.mark.unit
def test_unified_searchName_routes_to_edgar():
    """영문 키워드는 EDGAR 라우팅."""
    import dartlab

    r = dartlab.searchName("INTC")
    assert r.height > 0
    assert "INTC" in r["종목코드"].to_list()


@pytest.mark.unit
def test_korean_alias_routes_to_edgar():
    """'인텔' 한글 검색 → Intel(INTC) 또는 인텔리안(189300)."""
    import dartlab

    r = dartlab.searchName("인텔")
    assert r.height > 0
    codes = r["종목코드"].to_list()
    # 한글 alias 로 INTC 포함되거나, 최소 인텔리안(189300) 은 잡혀야 함
    assert "INTC" in codes or "189300" in codes


@pytest.mark.unit
def test_nameAliases_lookup():
    """KR→EN alias 사전 동작."""
    from dartlab.core.utils.nameAliases import resolveEnglishAlias

    assert resolveEnglishAlias("인텔") == "Intel"
    assert resolveEnglishAlias("애플") == "Apple"
    assert resolveEnglishAlias("엔비디아") == "NVIDIA"
    assert resolveEnglishAlias("알수없는기업") is None

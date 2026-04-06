"""dartlab.listing() 단일 진입점 facade 테스트."""

from __future__ import annotations

import polars as pl
import pytest

import dartlab

pytestmark = pytest.mark.unit


def test_listing_companies_default_backward_compat():
    """인자 없이 호출 = 기존 dartlab.listing() 동작 (KR 전 종목)."""
    df = dartlab.listing()
    assert isinstance(df, pl.DataFrame)
    assert df.height > 0
    # KIND 컬럼 — 회사명 또는 종목명 존재
    assert any(c in df.columns for c in ("회사명", "종목명", "name"))


def test_listing_companies_explicit_kind():
    df = dartlab.listing("companies")
    assert isinstance(df, pl.DataFrame)
    assert df.height > 0


def test_listing_korean_alias():
    df = dartlab.listing("기업")
    assert isinstance(df, pl.DataFrame)
    assert df.height > 0


def test_listing_filings_dart():
    df = dartlab.listing("filings", corp="005930")
    assert isinstance(df, pl.DataFrame)
    if df.height > 0:
        assert {"id", "date", "url", "reportType", "period"}.issubset(df.columns)
        # 원본 컬럼도 보존
        assert "rceptNo" in df.columns
        # url은 DART 뷰어 링크
        url0 = df["url"][0]
        assert url0 is not None and url0.startswith("http")


def test_listing_topics_dart():
    df = dartlab.listing("topics", corp="005930")
    assert isinstance(df, pl.DataFrame)
    assert {"topic", "summary"}.issubset(df.columns)


def test_listing_unknown_kind_raises():
    with pytest.raises(ValueError, match="unknown kind"):
        dartlab.listing("nope")


def test_listing_filings_requires_corp():
    with pytest.raises(ValueError, match="requires corp"):
        dartlab.listing("filings")


def test_listing_topics_requires_corp():
    with pytest.raises(ValueError, match="requires corp"):
        dartlab.listing("topics")

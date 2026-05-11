"""EDGAR docs namespace — sections 수평화가 유일한 기초 경로."""

from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl

from dartlab.core.memory import _CACHE_MISSING
from dartlab.core.polarsUtil import isEmptyDf

if TYPE_CHECKING:
    from dartlab.providers.edgar.company import Company


class _DocsAccessor:
    """EDGAR docs namespace. sections 수평화가 유일한 기초 경로.

    lazy-build 는 atomic 패턴 — ``cache.get(key, _CACHE_MISSING)`` 로 한 번만 cache 접
    근, 결과는 로컬 var 에 저장. ``cache[key] = val`` 직후 BoundedCache 의 FATAL/
    EMERGENCY clear 가 발동해 evict 되어도 ``return val`` 은 영향 없음. R9 인텔 audit
    의 ``KeyError: '_docs_sections'`` 결함 (2026-04-27) 의 근본 fix.
    """

    def __init__(self, company: Company):
        self._company = company

    @property
    def sections(self) -> pl.DataFrame | None:
        """sections — TODO 한국어 동작 설명."""
        key = "_docs_sections"
        val = self._company._cache.get(key, _CACHE_MISSING)
        if val is _CACHE_MISSING:
            from dartlab.providers.edgar.docs.sections.pipeline import sections

            val = sections(self._company.ticker)
            self._company._cache[key] = val
        return val

    @property
    def retrievalBlocks(self) -> pl.DataFrame | None:
        """retrievalBlocks — TODO 한국어 동작 설명."""
        key = "_docs_retrievalBlocks"
        val = self._company._cache.get(key, _CACHE_MISSING)
        if val is _CACHE_MISSING:
            from dartlab.providers.edgar.docs.sections.views import retrievalBlocks

            val = retrievalBlocks(self._company.ticker)
            self._company._cache[key] = val
        return val

    @property
    def contextSlices(self) -> pl.DataFrame | None:
        """contextSlices — TODO 한국어 동작 설명."""
        key = "_docs_contextSlices"
        val = self._company._cache.get(key, _CACHE_MISSING)
        if val is _CACHE_MISSING:
            from dartlab.providers.edgar.docs.sections.views import contextSlices

            val = contextSlices(self._company.ticker)
            self._company._cache[key] = val
        return val

    def notes(self, query: str | None = None) -> pl.DataFrame | None:
        """XBRL TextBlock 주석 검색 (원본). query=None이면 전체 목록."""
        from dartlab.providers.edgar.docs.notes import notes

        return notes(self._company.cik, query)

    def notesByCategory(self, category: str | None = None):
        """카테고리별 구조화 Notes. DART 의 ``c.show("inventory")`` 등에 대응.

        category=None이면 데이터 있는 카테고리 dict 반환.
        """
        from dartlab.providers.edgar.docs.notes import notesByCategory

        return notesByCategory(self._company.cik, category)

    def noteCategories(self) -> list[str]:
        """이 기업에서 데이터가 있는 notes 카테고리 목록."""
        from dartlab.providers.edgar.docs.notes import noteCategories

        return noteCategories(self._company.cik)

    def freq(self) -> pl.DataFrame | None:
        """freq — TODO 한국어 동작 설명."""
        key = "_docs_freq"
        val = self._company._cache.get(key, _CACHE_MISSING)
        if val is _CACHE_MISSING:
            from dartlab.providers.edgar.docs.sections.views import freq

            val = freq(self._company.ticker)
            self._company._cache[key] = val
        return val

    def coverage(self) -> pl.DataFrame | None:
        """coverage — TODO 한국어 동작 설명."""
        key = "_docs_coverage"
        val = self._company._cache.get(key, _CACHE_MISSING)
        if val is _CACHE_MISSING:
            from dartlab.providers.edgar.docs.sections.views import coverage

            val = coverage(self._company.ticker)
            self._company._cache[key] = val
        return val

    def filings(self) -> pl.DataFrame | None:
        """filings — TODO 한국어 동작 설명."""
        key = "_docs_filings"
        if key in self._company._cache:
            return self._company._cache[key]

        from dartlab.core.dataLoader import loadData

        df = loadData(self._company.ticker, category="edgarDocs")
        if isEmptyDf(df):
            self._company._cache[key] = None
            return None

        cols = ["period_key", "form_type", "accession_no", "filed_date"]
        available = [c for c in cols if c in df.columns]
        result = (
            df.select(available).unique(subset=["accession_no"]).sort("period_key", descending=True, nulls_last=True)
        )
        self._company._cache[key] = result
        return result

"""EDGAR pipeline.sections() 신우선/구fallback + raw wide loader 가드 — PR-E4.

본 PR-E4 단독 검증:
- ``pipeline.sections()`` 가 sectionsStorage artifact 있을 때 mmap path 우선
- artifact 부재 시 ``_legacySectionsBuild`` 자동 fallback (호출 검증)
- ``DARTLAB_EDGAR_LEGACY=1`` 환경변수 강제 fallback
- ``loadSectionsWide(valueColumn="content_raw")`` 가 raw HTML pivot wide 반환
"""

from __future__ import annotations

import os
from unittest.mock import patch

import polars as pl

from dartlab.providers.edgar.docs.sections import pipeline as pipelineMod
from dartlab.providers.edgar.docs.sections.sectionsBuilder import (
    buildSectionRowsFromFiling,
    emitPeriodArtifacts,
    removeSectionsArtifact,
)

_FIXTURE_TICKER = "TEST_PIPELINE_FIXTURE"


def _seedArtifact(ticker: str = _FIXTURE_TICKER) -> None:
    """fixture ticker 의 sections artifact 1 분기 생성."""
    rows = buildSectionRowsFromFiling(
        items=[{"title": "Item 1. Business", "content": "Para."}],
        rawHtml="<html><body><p>X</p></body></html>",
        formType="10-K",
        meta={
            "ticker": ticker,
            "cik": "c",
            "accession_no": "a",
            "form_type": "10-K",
            "period_key": "2024Q4",
            "year": 2024,
        },
    )
    emitPeriodArtifacts(ticker, rows)


def test_sections_uses_artifact_when_present() -> None:
    """artifact 있을 때 sectionsStorage path → docs.parquet read 0."""
    removeSectionsArtifact(_FIXTURE_TICKER)
    _seedArtifact(_FIXTURE_TICKER)
    try:
        # _legacySectionsBuild 가 호출되지 않음을 검증 (mock).
        with patch.object(pipelineMod, "_legacySectionsBuild") as legacy:
            legacy.return_value = pl.DataFrame()  # fallback 호출 시 빈 결과
            df = pipelineMod.sections(_FIXTURE_TICKER)
            assert df is not None
            assert not df.is_empty()
            legacy.assert_not_called()
    finally:
        removeSectionsArtifact(_FIXTURE_TICKER)


def test_sections_falls_back_when_artifact_absent() -> None:
    """artifact 부재 시 _legacySectionsBuild 호출."""
    removeSectionsArtifact(_FIXTURE_TICKER)
    # HF download 차단 — 진짜 부재 보장.
    os.environ["DARTLAB_NO_HF_DOWNLOAD"] = "1"
    try:
        with patch.object(pipelineMod, "_legacySectionsBuild") as legacy:
            legacy.return_value = pl.DataFrame({"topic": ["fallback"]})
            df = pipelineMod.sections(_FIXTURE_TICKER)
            legacy.assert_called_once_with(_FIXTURE_TICKER, sinceYear=None)
            assert df is not None
            assert df["topic"].to_list() == ["fallback"]
    finally:
        os.environ.pop("DARTLAB_NO_HF_DOWNLOAD", None)


def test_sections_force_legacy_env() -> None:
    """DARTLAB_EDGAR_LEGACY=1 시 artifact 있어도 fallback 강제."""
    removeSectionsArtifact(_FIXTURE_TICKER)
    _seedArtifact(_FIXTURE_TICKER)
    os.environ["DARTLAB_EDGAR_LEGACY"] = "1"
    try:
        with patch.object(pipelineMod, "_legacySectionsBuild") as legacy:
            legacy.return_value = pl.DataFrame({"topic": ["forced_fallback"]})
            df = pipelineMod.sections(_FIXTURE_TICKER)
            legacy.assert_called_once()
            assert df is not None
            assert df["topic"].to_list() == ["forced_fallback"]
    finally:
        os.environ.pop("DARTLAB_EDGAR_LEGACY", None)
        removeSectionsArtifact(_FIXTURE_TICKER)


def test_sections_raw_public_facade_removed() -> None:
    """공개 raw sections facade 는 폐기 — raw wide 는 storage helper 내부 경로."""
    from dartlab.providers.edgar.company import Company
    from dartlab.providers.edgar.docs.sections.sectionsStorage import hasSectionsArtifact, loadSectionsWide

    removeSectionsArtifact(_FIXTURE_TICKER)
    os.environ["DARTLAB_NO_HF_DOWNLOAD"] = "1"
    try:
        assert not hasattr(Company, "sectionsRaw")
        assert hasSectionsArtifact(_FIXTURE_TICKER) is False
        assert loadSectionsWide(_FIXTURE_TICKER, valueColumn="content_raw") is None
    finally:
        os.environ.pop("DARTLAB_NO_HF_DOWNLOAD", None)


def test_sections_raw_loader_returns_wide_with_content_raw() -> None:
    """artifact 있을 때 storage loader 는 raw HTML pivot wide 반환."""
    from dartlab.providers.edgar.docs.sections.sectionsStorage import loadSectionsWide

    removeSectionsArtifact(_FIXTURE_TICKER)
    _seedArtifact(_FIXTURE_TICKER)
    try:
        raw = loadSectionsWide(_FIXTURE_TICKER, valueColumn="content_raw")
        assert raw is not None
        # period 컬럼 1 개 이상 (2024Q4 또는 그 양식).
        periodCols = [c for c in raw.columns if len(c) >= 4 and c[:4].isdigit()]
        assert periodCols, f"period 컬럼 없음 (columns={raw.columns})"
        # 그 컬럼 cell 에 raw HTML 단편 포함 (<p> 또는 <html> 등 태그).
        firstPeriod = periodCols[0]
        cellValues = [v for v in raw[firstPeriod].to_list() if v]
        assert cellValues, "cell value 없음"
        joined = "\n".join(cellValues)
        assert "<" in joined, "raw HTML 태그 없음 — sanitize 가 너무 강함"
    finally:
        removeSectionsArtifact(_FIXTURE_TICKER)


def test_legacy_build_helper_callable() -> None:
    """_legacySectionsBuild 가 module-level function 으로 노출 (fallback 진입점)."""
    assert callable(pipelineMod._legacySectionsBuild)


def test_sections_lazy_pivot_excludes_old_periods() -> None:
    """sinceYear 인자 — 새 path 도 그 이전 period 컬럼 drop."""
    removeSectionsArtifact(_FIXTURE_TICKER)
    # 두 분기 (2024Q4 + 2020Q4) seed.
    rows1 = buildSectionRowsFromFiling(
        items=[{"title": "Item 1. Business", "content": "P1"}],
        rawHtml="<p>x</p>",
        formType="10-K",
        meta={
            "ticker": _FIXTURE_TICKER,
            "cik": "c",
            "accession_no": "a1",
            "form_type": "10-K",
            "period_key": "2024Q4",
            "year": 2024,
        },
    )
    rows2 = buildSectionRowsFromFiling(
        items=[{"title": "Item 1. Business", "content": "P2"}],
        rawHtml="<p>y</p>",
        formType="10-K",
        meta={
            "ticker": _FIXTURE_TICKER,
            "cik": "c",
            "accession_no": "a2",
            "form_type": "10-K",
            "period_key": "2020Q4",
            "year": 2020,
        },
    )
    emitPeriodArtifacts(_FIXTURE_TICKER, rows1 + rows2)
    try:
        df = pipelineMod.sections(_FIXTURE_TICKER, sinceYear=2023)
        assert df is not None
        periodCols = [c for c in df.columns if len(c) >= 4 and c[:4].isdigit()]
        assert "2024Q4" in periodCols
        assert "2020Q4" not in periodCols, "sinceYear 가 옛 period 컬럼 drop 못 함"
    finally:
        removeSectionsArtifact(_FIXTURE_TICKER)

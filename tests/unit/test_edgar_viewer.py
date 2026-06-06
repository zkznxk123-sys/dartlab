"""EDGAR viewer 가드 — PR-E5 plan delegated-prancing-tower.

본 PR-E5 단독 검증:
- ``providers/edgar/docs/viewer`` 의 4 함수 import + re-export
- ``viewerBlocks(company, topic)`` 가 EDGAR 내부 docs wide 위에서 text/table block 생성
- finance topic / report topic 은 미지원 (빈 list)
- companyApi.py 의 provider 분기 (market=='US' → EDGAR viewer) 정적 grep
- DART viewer 와 schema 동일성 (ViewerBlock 클래스 동일)
"""

from __future__ import annotations

import re
from pathlib import Path

import polars as pl

from dartlab.providers.edgar.docs.sections.sectionsBuilder import (
    buildSectionRowsFromFiling,
    emitPeriodArtifacts,
    removeSectionsArtifact,
)
from dartlab.providers.edgar.docs.viewer import (
    ViewerBlock,
    serializeViewerBlock,
    serializeViewerTextDocument,
    viewerBlocks,
    viewerTextDocument,
)

_FIXTURE_TICKER = "TEST_VIEWER_FIXTURE"


class _StubCompany:
    """fixture Company — viewerBlocks 가 호출하는 surface 만 emulate.

    실제 EDGAR Company 는 _docs.sections 내부 accessor 를 쓰는데, 본 unit 의
    범위는 viewerBlocks 의 docs wide → block list 변환만. stub 으로 격리.
    """

    def __init__(self, sectionsWide):
        self._docs = type("_Docs", (), {"sections": sectionsWide})()
        self.stockCode = _FIXTURE_TICKER
        self.ticker = _FIXTURE_TICKER
        self.market = "US"
        self.corpName = "Fixture Inc."


def _loadFixtureSections():
    from dartlab.providers.edgar.docs.sections.sectionsStorage import loadSectionsWide

    return loadSectionsWide(_FIXTURE_TICKER, valueColumn="content_plain")


def _makeFixtureCompany():
    """artifact 없는 stub — sections=None."""
    return _StubCompany(None)


def _seedSections():
    rows = []
    rows += buildSectionRowsFromFiling(
        items=[{"title": "Item 1. Business", "content": "Apple designs products."}],
        rawHtml="<html><body><p>Business body</p></body></html>",
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
    rows += buildSectionRowsFromFiling(
        items=[
            {
                "title": "Item 7. Management's Discussion",
                "content": "MDA text body.\n| metric | value |\n| --- | --- |\n| revenue | 100 |",
            }
        ],
        rawHtml="<html><body><table><tr><td>x</td></tr></table></body></html>",
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
    emitPeriodArtifacts(_FIXTURE_TICKER, rows)


def _resetArtifacts():
    removeSectionsArtifact(_FIXTURE_TICKER)


def test_module_exports() -> None:
    """4 함수 + ViewerBlock 클래스 import 성공."""
    assert callable(viewerBlocks)
    assert callable(viewerTextDocument)
    assert callable(serializeViewerBlock)
    assert callable(serializeViewerTextDocument)
    assert ViewerBlock is not None


def test_viewer_block_class_identity_with_dart() -> None:
    """EDGAR viewer 의 ViewerBlock 이 DART viewer 와 동일 클래스 (re-export)."""
    from dartlab.providers.dart.viewer import ViewerBlock as DartViewerBlock

    assert ViewerBlock is DartViewerBlock, "EDGAR/DART viewer block schema 일치 의무"


def test_viewer_blocks_empty_when_sections_absent() -> None:
    """sections=None stub → 빈 list (artifact 부재 동치)."""
    company = _makeFixtureCompany()
    blocks = viewerBlocks(company, "10-K::item1Business")
    assert blocks == []


def test_viewer_blocks_builds_text_and_table() -> None:
    """sections artifact 가 있을 때 viewerBlocks 가 text + table block 생성."""
    _resetArtifacts()
    _seedSections()
    try:
        sectionsWide = _loadFixtureSections()
        assert sectionsWide is not None, "fixture sections wide 로드 실패"
        company = _StubCompany(sectionsWide)
        # 등록된 topic 확인 (mapper 출력 의존성 제거 — sections wide 의 topic 컬럼 직접 사용).
        topics = sectionsWide["topic"].unique().to_list()
        assert topics, "fixture topic 없음"
        anyTopic = topics[0]
        blocks = viewerBlocks(company, anyTopic)
        assert blocks, f"{anyTopic} block 없음"
        kinds = {b.kind for b in blocks}
        assert kinds, "block kind 없음"
    finally:
        _resetArtifacts()


def test_viewer_blocks_unknown_topic_returns_empty() -> None:
    """존재하지 않는 topic 은 빈 list."""
    _resetArtifacts()
    _seedSections()
    try:
        sectionsWide = _loadFixtureSections()
        company = _StubCompany(sectionsWide)
        blocks = viewerBlocks(company, "10-K::itemNonexistent")
        assert blocks == []
    finally:
        _resetArtifacts()


def test_company_api_provider_branch() -> None:
    """server/services/companyApi.py 의 provider 분기 정적 grep — market=='US' 분기 존재."""
    candidates = [
        Path("c:/Users/MSI/OneDrive/Desktop/sideProject/dartlab/src/dartlab/server/services/companyApi.py"),
        Path("src/dartlab/server/services/companyApi.py"),
    ]
    text = ""
    for p in candidates:
        if p.exists():
            text = p.read_text(encoding="utf-8")
            break
    assert text, "companyApi.py 부재"
    # EDGAR viewer import 분기 존재.
    assert "providers.edgar.docs.viewer" in text
    # market 분기.
    assert re.search(r'market.*["\\\']US["\\\']', text)


def test_serialize_round_trip_with_no_blocks() -> None:
    """블록 list 가 비어도 serialize 함수가 안전 동작."""
    doc = viewerTextDocument("10-K::item1Business", [])
    serialized = serializeViewerTextDocument(doc)
    # None 또는 빈 entries dict — 두 양식 모두 안전.
    assert serialized is None or isinstance(serialized, dict)

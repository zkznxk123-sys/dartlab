"""panel grid viewer 백엔드 (server.services.companyApi) 테스트.

``serializePanelRows`` / ``sectionKeyFor`` / ``splitSectionKey`` 는 순수 함수
(실데이터 불요). ``buildToc`` / ``buildPanelGrid`` 는 Company.panel artifact 필요
(``requires_data`` — 로컬 005930 있으면 실행, 없으면 skip).

plan silly-snacking-yeti — 공시뷰어 panel SSOT 재구축.
"""

from __future__ import annotations

import polars as pl
import pytest

from dartlab.server.services.companyApi import (
    _viewerUrlForFiling,
    sectionKeyFor,
    serializePanelRows,
    splitSectionKey,
)

SAMSUNG = "005930"


def _sampleWide() -> pl.DataFrame:
    """panel wide 모사 — narrative(TITLE/P) + 표(TABLE) 혼합."""
    return pl.DataFrame(
        {
            "chapter": ["I. 회사의 개요", "I. 회사의 개요", "III. 재무에 관한 사항"],
            "sectionLeaf": ["1. 회사의 개요", "1. 회사의 개요", "2. 연결재무제표"],
            "blockLeaf": ["", "연혁표", "연결 재무상태표"],
            "disclosureKey": [None, None, "BS"],
            "scope": ["consolidated", "consolidated", "consolidated"],
            "2025Q4": [
                "<TITLE>개요</TITLE><P>본문</P>",
                "<TABLE-GROUP><TABLE><TR><TE>a</TE></TR></TABLE></TABLE-GROUP>",
                "<TABLE><TR><TE>100</TE></TR></TABLE>",
            ],
            "2024Q4": ["<P>옛 본문</P>", "", None],
        }
    )


class TestViewerUrlForFiling:
    """공시 뷰어 URL 시장분기 — KR=DART(rcpNo), US=SEC EDGAR(filing index)."""

    def test_kr_dart_url(self):
        url = _viewerUrlForFiling(isUs=False, rceptNo="20260515002181", cik=None)
        assert url == "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260515002181"

    def test_us_sec_url(self):
        # rceptNo = SEC accession, cik leading-zero strip + accession 무하이픈 경로.
        url = _viewerUrlForFiling(isUs=True, rceptNo="0000320193-25-000079", cik="0000320193")
        assert url == "https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/0000320193-25-000079-index.htm"

    def test_us_without_cik_returns_none(self):
        # cik 없으면 SEC URL 생성 불가 → None (잘못된 DART URL 박지 않음).
        assert _viewerUrlForFiling(isUs=True, rceptNo="0000320193-25-000079", cik=None) is None


class TestSerializePanelRows:
    def test_blockType_table_vs_text(self):
        rows = serializePanelRows(_sampleWide(), ["2025Q4", "2024Q4"])
        byBlock = {r["blockLeaf"]: r for r in rows}
        assert byBlock[""]["blockType"] == "text"  # narrative
        assert byBlock["연혁표"]["blockType"] == "table"  # <TABLE 포함
        assert byBlock["연결 재무상태표"]["blockType"] == "table"

    def test_skip_empty_rows(self):
        df = pl.DataFrame(
            {
                "chapter": ["I"],
                "sectionLeaf": ["s"],
                "blockLeaf": [""],
                "disclosureKey": [None],
                "scope": ["consolidated"],
                "2025Q4": [""],
                "2024Q4": [None],
            }
        )
        assert serializePanelRows(df, ["2025Q4", "2024Q4"]) == []

    def test_drop_empty_cells(self):
        rows = serializePanelRows(_sampleWide(), ["2025Q4", "2024Q4"])
        bs = next(r for r in rows if r["disclosureKey"] == "BS")
        assert "2025Q4" in bs["cells"]
        assert "2024Q4" not in bs["cells"]  # 빈/None 셀 drop

    def test_no_blockOrder_field(self):
        rows = serializePanelRows(_sampleWide(), ["2025Q4"])
        assert rows
        assert "blockOrder" not in rows[0]  # SPINE 정렬 — blockOrder 불요


class TestSectionKey:
    def test_roundtrip(self):
        key = sectionKeyFor("I. 회사의 개요", "1. 회사의 개요")
        chapter, section = splitSectionKey(key)
        assert chapter == "I. 회사의 개요"
        assert section == "1. 회사의 개요"

    def test_no_separator(self):
        chapter, section = splitSectionKey("plain")
        assert chapter is None
        assert section == "plain"


@pytest.mark.requires_data
class TestPanelIntegration:
    def test_buildToc_chapters_and_periods(self):
        from dartlab import Company
        from dartlab.server.services.companyApi import buildToc

        toc = buildToc(Company(SAMSUNG))
        assert isinstance(toc["chapters"], list)
        if not toc["chapters"]:
            pytest.skip("panel artifact 없음 (005930)")
        sec0 = toc["chapters"][0]["sections"][0]
        assert "children" not in sec0  # 옛 chapter III 그루핑 제거
        assert "sectionKey" in sec0 and "sectionLeaf" in sec0
        assert toc["periods"]  # 전체 기간 축 (최신좌측)

    def test_buildPanelGrid_window_slice(self):
        from dartlab import Company
        from dartlab.server.services.companyApi import buildPanelGrid, buildToc

        c = Company(SAMSUNG)
        toc = buildToc(c)
        if not toc["chapters"]:
            pytest.skip("panel artifact 없음 (005930)")
        periods = toc["periods"][:3]
        ch = toc["chapters"][0]
        sec = ch["sections"][0]
        grid = buildPanelGrid(c, chapter=ch["chapter"], section=sec["sectionLeaf"], windowPeriods=tuple(periods))
        wanted = set(periods)
        for r in grid["rows"]:
            assert set(r["cells"].keys()) <= wanted  # window 밖 셀 0
            assert r["cells"]  # 빈 행 0

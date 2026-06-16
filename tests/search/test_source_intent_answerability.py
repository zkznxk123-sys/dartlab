"""Product search source intent and answerability tests."""

from __future__ import annotations

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def _patchIndexDir(monkeypatch, tmp_path):
    from dartlab.providers.dart.search import api, fieldIndex, unified

    monkeypatch.setattr(fieldIndex, "_contentIndexDir", lambda tier=None: tmp_path)
    monkeypatch.setattr(fieldIndex, "_activeIndexDir", lambda: tmp_path)
    monkeypatch.setattr(unified, "_activeIndexDir", lambda: tmp_path)
    monkeypatch.setattr(api, "_prefersTitleLane", lambda query: False)
    monkeypatch.setenv("DARTLAB_NO_HF_DOWNLOAD", "1")
    return fieldIndex


def _buildMain(fieldIndex, rows):
    idx, meta = fieldIndex.buildContentSegment(rows, showProgress=False)
    fieldIndex.saveSegment(idx, meta, "main")
    fieldIndex.clearCache()


def _row(rcept: str, content: str, *, source: str, date: str = "20260615", url: str = "") -> dict:
    return {
        "rcept_no": rcept,
        "section_order": 0,
        "corp_code": "00126380" if source != "news" else "",
        "corp_name": "삼성전자" if source != "news" else "",
        "stock_code": "005930" if source != "news" else "",
        "rcept_dt": date,
        "report_nm": "주요사항보고서" if source != "news" else "",
        "section_title": "자금조달" if source != "news" else "시장 뉴스",
        "section_content": content,
        "source": source,
        "sourceDataAsOf": date,
        "url": url,
    }


def test_detect_source_intent_general_policy() -> None:
    from dartlab.providers.dart.search.sourceIntent import detectSourceIntent

    assert detectSourceIntent("공시 말고 뉴스 유상증자").kind == "news"
    assert detectSourceIntent("뉴스 말고 공시 유상증자").kind == "filing"
    assert detectSourceIntent("반도체 뉴스").kind == "news"
    assert detectSourceIntent("공시 원문 대표이사 변경").kind == "filing"
    assert detectSourceIntent("반도체 뉴스와 공시 비교").kind == "all"
    assert detectSourceIntent("유상증자", explicitScope="news").kind == "news"


def test_auto_news_intent_uses_news_source_even_when_filings_dominate(tmp_path, monkeypatch) -> None:
    import dartlab

    fieldIndex = _patchIndexDir(monkeypatch, tmp_path)
    rows = [_row(f"202606150000{i:02d}", "유상증자 결정 공시 본문 운영자금", source="allFilings") for i in range(25)]
    rows.append(
        _row(
            "news:raising",
            "유상증자 관련 속보 기사와 시장 반응",
            source="news",
            url="https://n.example/raising",
        )
    )
    _buildMain(fieldIndex, rows)

    df = dartlab.search("공시 말고 뉴스 유상증자", scope="auto", limit=5)
    assert df.height == 1
    assert set(df["source"].to_list()) == {"news"}
    assert df.row(0, named=True)["sourceRef"] == "news:raising"


def test_auto_filing_intent_excludes_news(tmp_path, monkeypatch) -> None:
    import dartlab

    fieldIndex = _patchIndexDir(monkeypatch, tmp_path)
    _buildMain(
        fieldIndex,
        [
            _row("20260615000001", "유상증자 결정 공시 본문 운영자금", source="allFilings"),
            _row("news:raising", "유상증자 관련 속보 기사", source="news", url="https://n.example/raising"),
        ],
    )

    df = dartlab.search("뉴스 말고 공시 유상증자", scope="auto", limit=5)
    assert df.height >= 1
    assert "news" not in set(df["source"].to_list())
    assert df.row(0, named=True)["sourceRef"].startswith("dart:")


def test_answerability_marks_missing_evidence_and_source_mismatch() -> None:
    from dartlab.providers.dart.search.answerability import applyAnswerability
    from dartlab.providers.dart.search.facetPlanner import QueryFacets
    from dartlab.providers.dart.search.resultSchema import normalizeSearchResult
    from dartlab.providers.dart.search.sourceIntent import detectSourceIntent

    rows = normalizeSearchResult(
        pl.DataFrame(
            [
                {
                    "source": "news",
                    "rcept_no": "news:1",
                    "snippet": "뉴스 근거",
                    "sourceRef": "news:1",
                    "dataAsOf": "20260615",
                },
                {
                    "source": "allFilings",
                    "rcept_no": "",
                    "snippet": "공시 근거",
                    "sourceRef": "",
                    "dataAsOf": "20260615",
                },
            ]
        )
    )

    out = applyAnswerability(rows, sourceIntent=detectSourceIntent("뉴스 말고 공시 유상증자"))
    bySource = {row["source"]: row for row in out.iter_rows(named=True)}
    assert bySource["news"]["answerable"] is False
    assert bySource["news"]["notAnswerableReason"] == "sourceIntentMismatch"
    assert bySource["allFilings"]["answerable"] is False
    assert bySource["allFilings"]["notAnswerableReason"] == "missingSourceRef"

    out2 = applyAnswerability(rows, facets=QueryFacets(receiptNumbers=("20260615000001",)))
    bySource2 = {row["source"]: row for row in out2.iter_rows(named=True)}
    assert bySource2["news"]["notAnswerableReason"] == "facetMismatch:receipt"


def test_public_search_marks_report_facet_mismatch(tmp_path, monkeypatch) -> None:
    import dartlab

    fieldIndex = _patchIndexDir(monkeypatch, tmp_path)
    _buildMain(
        fieldIndex,
        [
            _row(
                "20260615000001",
                "대표이사 변경 공시 본문",
                source="allFilings",
                date="20260615",
            )
        ],
    )

    df = dartlab.search("대표이사 사업보고서", scope="content", limit=5)
    assert df.height == 1
    top = df.row(0, named=True)
    assert top["answerable"] is False
    assert top["notAnswerableReason"] == "facetMismatch:report"


def test_public_search_marks_stale_latest_query(tmp_path, monkeypatch) -> None:
    import dartlab

    fieldIndex = _patchIndexDir(monkeypatch, tmp_path)
    _buildMain(
        fieldIndex,
        [
            _row(
                "20200101000001",
                "유상증자 결정 공시 본문",
                source="allFilings",
                date="20200101",
            )
        ],
    )

    df = dartlab.search("최신 유상증자 공시", scope="content", limit=5)
    assert df.height == 1
    top = df.row(0, named=True)
    assert top["answerable"] is False
    assert top["notAnswerableReason"] == "staleSource"


def test_public_search_uses_company_name_in_query_as_stock_filter(tmp_path, monkeypatch) -> None:
    import dartlab

    class FakeResolver:
        def nameToCode(self, name: str) -> str | None:
            return {"삼성전자": "005930"}.get(name)

    import dartlab.core.listingResolver as listingResolver

    monkeypatch.setattr(listingResolver, "getListingResolver", lambda: FakeResolver())
    fieldIndex = _patchIndexDir(monkeypatch, tmp_path)
    _buildMain(
        fieldIndex,
        [
            {
                "rcept_no": "20260615000001",
                "section_order": 0,
                "corp_code": "00126380",
                "corp_name": "삼성전자",
                "stock_code": "005930",
                "rcept_dt": "20260615",
                "report_nm": "대표이사(대표집행임원)변경(안내공시)",
                "section_title": "대표이사",
                "section_content": "대표이사 변경 공시 본문",
                "source": "allFilings",
                "sourceDataAsOf": "20260615",
            },
            {
                "rcept_no": "20260615000002",
                "section_order": 0,
                "corp_code": "00126256",
                "corp_name": "삼성카드",
                "stock_code": "029780",
                "rcept_dt": "20260615",
                "report_nm": "대표이사(대표집행임원)변경(안내공시)",
                "section_title": "대표이사",
                "section_content": "대표이사 변경 공시 본문",
                "source": "allFilings",
                "sourceDataAsOf": "20260615",
            },
        ],
    )

    df = dartlab.search("삼성전자 대표이사 변경", scope="content", limit=5)

    assert df.height == 1
    assert df.row(0, named=True)["stock_code"] == "005930"
    assert df.row(0, named=True)["corp_name"] == "삼성전자"

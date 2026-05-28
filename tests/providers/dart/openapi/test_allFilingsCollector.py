"""providers/dart/openapi/allFilingsCollector.py mirror smoke — P6."""

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.openapi.allFilingsCollector  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_collect_meta_day_callable() -> None:
    """collectMetaDay() callable smoke."""
    from dartlab.providers.dart.openapi.allFilingsCollector import collectMetaDay

    assert callable(collectMetaDay)


def test_collect_meta_range_callable() -> None:
    """collectMetaRange() callable smoke."""
    from dartlab.providers.dart.openapi.allFilingsCollector import collectMetaRange

    assert callable(collectMetaRange)


def test_collected_dates_callable() -> None:
    """collectedDates() callable smoke."""
    from dartlab.providers.dart.openapi.allFilingsCollector import collectedDates

    assert callable(collectedDates)


def test_fill_content_callable() -> None:
    """fillContent() callable smoke."""
    from dartlab.providers.dart.openapi.allFilingsCollector import fillContent

    assert callable(fillContent)


def test_fill_content_all_callable() -> None:
    """fillContentAll() callable smoke."""
    from dartlab.providers.dart.openapi.allFilingsCollector import fillContentAll

    assert callable(fillContentAll)


def test_load_all_callable() -> None:
    """loadAll() callable smoke."""
    from dartlab.providers.dart.openapi.allFilingsCollector import loadAll

    assert callable(loadAll)


def test_load_day_callable() -> None:
    """loadDay() callable smoke."""
    from dartlab.providers.dart.openapi.allFilingsCollector import loadDay

    assert callable(loadDay)


def test_pending_dates_callable() -> None:
    """pendingDates() callable smoke."""
    from dartlab.providers.dart.openapi.allFilingsCollector import pendingDates

    assert callable(pendingDates)


def test_stats_callable() -> None:
    """stats() callable smoke."""
    from dartlab.providers.dart.openapi.allFilingsCollector import stats

    assert callable(stats)


def _writeStubMeta(outDir, period: str, rceptNo: str) -> None:
    """공통 meta fixture writer."""
    metaRow = {
        "corp_code": "00126380",
        "corp_name": "삼성전자",
        "stock_code": "005930",
        "corp_cls": "Y",
        "rcept_dt": period,
        "rcept_no": rceptNo,
        "report_nm": "주요사항보고서(자기주식취득결정)",
        "flr_nm": "삼성전자",
    }
    pl.DataFrame([metaRow]).write_parquet(outDir / f"{period}_meta.parquet")


def _assertSchema(df) -> None:
    """공통 schema 회귀 가드 — content_raw 만, section_* 부재."""
    cols = set(df.columns)
    assert "content_raw" in cols, f"content_raw 컬럼 없음: {cols}"
    assert "section_content" not in cols, f"옛 section_content 컬럼 잔존: {cols}"
    assert "section_title" not in cols, f"옛 section_title 컬럼 잔존: {cols}"
    assert "section_order" not in cols, f"옛 section_order 컬럼 잔존: {cols}"


class _StubClient:
    pass


def test_fill_content_schema_raw_xml(monkeypatch, tmp_path) -> None:
    """fillContent 결과 schema 는 content_raw 만, DART dart4.xsd XML 태그·attribute 보존.

    DART 가 반환하는 두 포맷 중 (a) dart4.xsd XML 회귀 가드 — `<DOCUMENT>` /
    `<TITLE ATOC ...>` / `<TABLE>` 와 ATOC / AASSOCNOTE / ACODE attribute 가 raw
    그대로 살아있는지 확인.
    """
    import dartlab.config as _cfg
    from dartlab.providers.dart.openapi import allFilingsCollector as mod

    monkeypatch.setattr(_cfg, "dataDir", str(tmp_path))
    outDir = mod._allFilingsDir()
    _writeStubMeta(outDir, "20260527", "20260527000001")

    stubXml = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<DOCUMENT xsi:noNamespaceSchemaLocation="dart4.xsd">'
        '<DOCUMENT-NAME ACODE="10136">주요사항보고서</DOCUMENT-NAME>'
        '<BODY ATOCID="32">'
        '<TITLE ATOC="Y" AASSOCNOTE="COVER" ATOCID="1">개요</TITLE>'
        "<P>본문 시작</P>"
        '<TABLE BORDER="1"><TR><TD>항목</TD><TD>값</TD></TR></TABLE>'
        "<P>본문 끝</P>"
        "</BODY></DOCUMENT>"
    )
    monkeypatch.setattr(mod, "_collectOneRaw", lambda client, rceptNo: stubXml)

    df = mod.fillContent("20260527", client=_StubClient(), showProgress=False)
    assert df is not None
    _assertSchema(df)

    raw = df["content_raw"][0]
    assert "<DOCUMENT" in raw
    assert "<TITLE" in raw
    assert "<TABLE" in raw
    assert 'ATOC="Y"' in raw
    assert 'AASSOCNOTE="COVER"' in raw

    assert not (outDir / "20260527_meta.parquet").exists()
    assert (outDir / "20260527.parquet").exists()


def test_fill_content_schema_raw_html(monkeypatch, tmp_path) -> None:
    """fillContent 결과 schema 는 content_raw 만, xforms HTML 태그·attribute 보존.

    DART 가 반환하는 두 포맷 중 (b) xforms HTML 회귀 가드 — `<html>` / `<head>` /
    `<STYLE>` / `<meta charset>` 와 xforms CSS class 가 raw 그대로 살아있는지 확인.
    """
    import dartlab.config as _cfg
    from dartlab.providers.dart.openapi import allFilingsCollector as mod

    monkeypatch.setattr(_cfg, "dataDir", str(tmp_path))
    outDir = mod._allFilingsDir()
    _writeStubMeta(outDir, "20260528", "20260528000002")

    stubHtml = (
        "<html><head>"
        '<meta content="text/html; charset=euc-kr" http-equiv="Content-Type">'
        "<STYLE>.xforms * { font-family: 돋움체; } .xforms_title * { font-size: 13pt; }</STYLE>"
        '</head><body class="xforms">'
        '<table><tr><td class="xforms_title">최대주주변동</td></tr></table>'
        "</body></html>"
    )
    monkeypatch.setattr(mod, "_collectOneRaw", lambda client, rceptNo: stubHtml)

    df = mod.fillContent("20260528", client=_StubClient(), showProgress=False)
    assert df is not None
    _assertSchema(df)

    raw = df["content_raw"][0]
    assert "<html>" in raw
    assert "<STYLE>" in raw
    assert "xforms" in raw
    assert "charset=euc-kr" in raw

    assert not (outDir / "20260528_meta.parquet").exists()
    assert (outDir / "20260528.parquet").exists()

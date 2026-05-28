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


def test_fill_content_schema_html(monkeypatch, tmp_path) -> None:
    """fillContent 결과 schema 는 content_html 만 — section_* 3 컬럼 모두 부재.

    HTML 태그 (`<table>` · `<p>`) 가 raw 그대로 보존되는지 확인. 정공법 클린 컷오버
    회귀 가드 (옛 section_content / section_title / section_order 컬럼이 다시 생기면
    실패).
    """
    import dartlab.config as _cfg
    from dartlab.providers.dart.openapi import allFilingsCollector as mod

    # 격리된 임시 dataDir
    monkeypatch.setattr(_cfg, "dataDir", str(tmp_path))
    outDir = mod._allFilingsDir()

    # meta parquet 1 row 작성 (정기공시 패턴 회피)
    metaRow = {
        "corp_code": "00126380",
        "corp_name": "삼성전자",
        "stock_code": "005930",
        "corp_cls": "Y",
        "rcept_dt": "20260527",
        "rcept_no": "20260527000001",
        "report_nm": "주요사항보고서(자기주식취득결정)",
        "flr_nm": "삼성전자",
    }
    pl.DataFrame([metaRow]).write_parquet(outDir / "20260527_meta.parquet")

    # _collectOneHtml stub — raw HTML with 태그 보존
    stubHtml = (
        "<html><body><p>본문 시작</p><table><tr><td>항목</td><td>값</td></tr></table><p>본문 끝</p></body></html>"
    )

    def stubCollect(client, rceptNo):
        return stubHtml

    monkeypatch.setattr(mod, "_collectOneHtml", stubCollect)

    # client 도 stub (실제 API 호출 차단)
    class _StubClient:
        pass

    df = mod.fillContent("20260527", client=_StubClient(), showProgress=False)

    assert df is not None, "fillContent 결과 None — 승격 차단됐을 가능성"
    cols = set(df.columns)
    assert "content_html" in cols, f"content_html 컬럼 없음: {cols}"
    assert "section_content" not in cols, f"옛 section_content 컬럼 잔존: {cols}"
    assert "section_title" not in cols, f"옛 section_title 컬럼 잔존: {cols}"
    assert "section_order" not in cols, f"옛 section_order 컬럼 잔존: {cols}"

    htmlValue = df["content_html"][0]
    assert "<table>" in htmlValue, "HTML 태그 손실 — raw 보존 실패"
    assert "<p>" in htmlValue, "HTML 태그 손실 — raw 보존 실패"

    # _meta 는 승격 후 제거됨
    assert not (outDir / "20260527_meta.parquet").exists()
    assert (outDir / "20260527.parquet").exists()

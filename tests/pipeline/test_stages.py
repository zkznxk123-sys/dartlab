"""stage 충실성 — runScript 호출 인자가 워크플로와 동형인지(mock, 실행 0)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def _capture(monkeypatch, modname):
    """모듈의 runScript 를 호출 기록 mock 으로 교체."""
    import importlib

    mod = importlib.import_module(modname)
    calls: list[tuple] = []
    monkeypatch.setattr(mod, "runScript", lambda *a, **k: calls.append((a, k)) or 0)
    return mod, calls


def test_macro_faithful(monkeypatch):
    """macro — buildMacroData(--source --push) + buildMacroCycle(--push)."""
    monkeypatch.setenv("MACRO_SOURCE", "fred")
    mod, calls = _capture(monkeypatch, "dartlab.pipeline.stages.macro")
    res = mod.runMacro()
    assert calls[0][0] == (".github/scripts/sync/buildMacroData.py", "--source", "fred", "--push")
    assert calls[1][0] == (".github/scripts/sync/buildMacroCycle.py", "--push")
    assert res.report.ok == 1


def test_krx_incremental_and_backfill(monkeypatch):
    """krx — 기본 incremental, KRX_MODE=backfill 시 --start/--end 포함."""
    mod, calls = _capture(monkeypatch, "dartlab.pipeline.stages.krx")
    monkeypatch.delenv("KRX_MODE", raising=False)
    mod.runKrx()
    assert calls[-1][0] == (".github/scripts/sync/buildKrxData.py", "--mode", "incremental", "--push")
    monkeypatch.setenv("KRX_MODE", "backfill")
    monkeypatch.setenv("KRX_START", "2020")
    monkeypatch.setenv("KRX_END", "2024")
    mod.runKrxIndex()
    assert calls[-1][0] == (
        ".github/scripts/sync/buildKrxIndexData.py",
        "--mode",
        "backfill",
        "--start",
        "2020",
        "--end",
        "2024",
        "--push",
    )


def test_news_faithful(monkeypatch):
    """news — KR/US fetch(--once --max-queries) + bulkUploadHf(--since 86400)."""
    monkeypatch.setenv("NEWS_MAX_QUERIES_KR", "150")
    monkeypatch.setenv("NEWS_MAX_QUERIES_US", "80")
    mod, calls = _capture(monkeypatch, "dartlab.pipeline.stages.news")
    res = mod.runNewsHeadlines(upload=True)
    scripts = [c[0] for c in calls]
    assert scripts[0] == (
        ".github/scripts/sync/syncNewsHeadlines.py",
        "--market",
        "KR",
        "--once",
        "--max-queries",
        "150",
    )
    assert scripts[1] == (
        ".github/scripts/sync/syncNewsHeadlines.py",
        "--market",
        "US",
        "--once",
        "--max-queries",
        "80",
    )
    assert scripts[2] == (".github/scripts/sync/bulkUploadHf.py", "newsHeadlines", "--since", "86400")
    assert res.report.ok == 1


def test_news_no_upload(monkeypatch):
    """news --no-upload — bulkUploadHf 미호출."""
    mod, calls = _capture(monkeypatch, "dartlab.pipeline.stages.news")
    mod.runNewsHeadlines(upload=False)
    assert all("bulkUploadHf" not in c[0][0] for c in calls)


def test_edgar_four_quarters():
    """edgar 4분기 wrap — 분기 경계 음수 보정."""
    from dartlab.pipeline.stages.edgar import _fourQuarters

    assert _fourQuarters(2024, 2) == [(2024, 2), (2024, 1), (2023, 4), (2023, 3)]


def test_edgar_bulk_quarterly(monkeypatch):
    """edgar — companyfacts bulk + 4분기 download/convert 호출(누락분만)."""
    import dartlab.providers.edgar.bulk as bulk

    seen = {"convertQ": []}
    monkeypatch.setattr(bulk, "downloadCompanyfactsBulk", lambda **k: "/cf.zip")
    monkeypatch.setattr(bulk, "convertBulkToParquets", lambda **k: {"ok": 1})
    monkeypatch.setattr(bulk, "discoverLatestQuarter", lambda: (2024, 2))
    monkeypatch.setattr(bulk, "listLocalQuarters", lambda **k: [(2023, 4)])  # 1개 보유
    monkeypatch.setattr(bulk, "downloadQuarterlyDataset", lambda y, q, **k: f"/{y}Q{q}.zip")
    monkeypatch.setattr(
        bulk, "convertQuarterlyToParquets", lambda y, q, **k: seen["convertQ"].append((y, q)) or {"sub": 1}
    )

    from dartlab.pipeline.stages.edgar import runEdgar

    res = runEdgar()
    # 4분기 중 (2023,4) 보유 → 3개만 convert
    assert seen["convertQ"] == [(2024, 2), (2024, 1), (2023, 3)]
    assert res.report.ok == 2 and res.report.err == 0


def test_dart_recent_respects_sync_categories_env(monkeypatch):
    """dart recent — SYNC_CATEGORIES env(다중) 우선, 없으면 category 단일."""
    mod, calls = _capture(monkeypatch, "dartlab.pipeline.stages.dart")
    monkeypatch.setattr(mod, "readChanged", lambda c: [])
    monkeypatch.setenv("SYNC_CATEGORIES", "finance,report")
    mod.runDartRecent(category="finance", upload=False)
    assert calls[-1][1]["env"] == {"SYNC_CATEGORIES": "finance,report"}
    monkeypatch.delenv("SYNC_CATEGORIES", raising=False)
    mod.runDartRecent(category="report", upload=False)
    assert calls[-1][1]["env"] == {"SYNC_CATEGORIES": "report"}

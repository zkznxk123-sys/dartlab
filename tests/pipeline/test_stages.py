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

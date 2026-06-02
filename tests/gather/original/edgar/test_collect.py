"""gather.original.edgar.collect — archiveEdgarOriginals unit 테스트 (네트워크 0)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_archive_writes_txt_and_skips(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """archiveEdgarOriginals — .txt 저장(SGML 헤더) + 재실행 skip."""
    import dartlab.config as cfg
    from dartlab.gather.original import paths
    from dartlab.gather.original.edgar import collect

    monkeypatch.setattr(cfg, "dataDir", str(tmp_path))

    fakeRows = [
        {"cik": "0000320193", "accession_no": "0000320193-24-000002", "txt_url": "http://x/a.txt"},
    ]
    monkeypatch.setattr(collect, "listAllFilings", lambda *a, **k: fakeRows)
    monkeypatch.setattr(collect, "_fetchTxt", lambda url: b"<SEC-DOCUMENT>0000320193-24-000002.txt\n...")

    stats = collect.archiveEdgarOriginals(["AAPL"], forms=["8-K"], showProgress=False)
    outPath = paths.edgarDir("0000320193") / "0000320193-24-000002.txt"
    assert outPath.exists()
    assert outPath.read_bytes().startswith(b"<SEC-DOCUMENT>")
    assert stats["ok"] == 1

    stats2 = collect.archiveEdgarOriginals(["AAPL"], forms=["8-K"], showProgress=False)
    assert stats2["ok"] == 0 and stats2["skipped"] == 1


def test_archive_fetch_failure_counts_error(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """_fetchTxt None(실패) 이면 error 집계, 파일 미생성."""
    import dartlab.config as cfg
    from dartlab.gather.original import paths
    from dartlab.gather.original.edgar import collect

    monkeypatch.setattr(cfg, "dataDir", str(tmp_path))
    fakeRows = [{"cik": "0000320193", "accession_no": "0000320193-24-000099", "txt_url": "http://x/b.txt"}]
    monkeypatch.setattr(collect, "listAllFilings", lambda *a, **k: fakeRows)
    monkeypatch.setattr(collect, "_fetchTxt", lambda url: None)

    stats = collect.archiveEdgarOriginals(["AAPL"], showProgress=False)
    assert stats["error"] == 1 and stats["ok"] == 0
    assert not (paths.edgarDir("0000320193") / "0000320193-24-000099.txt").exists()

"""gather.original.edgar.collect — EDGAR text fetch helper unit 테스트 (네트워크 0)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_fetch_filing_texts_returns_records_without_writing(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """fetchFilingTexts — full-submission text 를 메모리 record 로 반환하고 raw 파일을 만들지 않는다."""
    import dartlab.config as cfg
    from dartlab.gather.original.edgar import collect

    monkeypatch.setattr(cfg, "dataDir", str(tmp_path))

    fakeRows = [
        {"cik": "0000320193", "accession_no": "0000320193-24-000002", "txt_url": "http://x/a.txt"},
    ]
    monkeypatch.setattr(collect, "_fetchTxt", lambda url: b"<SEC-DOCUMENT>0000320193-24-000002.txt\n...")

    grouped = collect.fetchFilingTexts(fakeRows)

    rec = grouped["0000320193"][0]
    assert rec["accession_no"] == "0000320193-24-000002"
    assert rec["text"].startswith("<SEC-DOCUMENT>")
    assert not (tmp_path / "original" / "edgar").exists()


def test_fetch_filing_texts_skips_fetch_failure(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """_fetchTxt None(실패) 이면 해당 filing 을 건너뛰고 파일을 만들지 않는다."""
    import dartlab.config as cfg
    from dartlab.gather.original.edgar import collect

    monkeypatch.setattr(cfg, "dataDir", str(tmp_path))
    fakeRows = [{"cik": "0000320193", "accession_no": "0000320193-24-000099", "txt_url": "http://x/b.txt"}]
    monkeypatch.setattr(collect, "_fetchTxt", lambda url: None)

    grouped = collect.fetchFilingTexts(fakeRows)

    assert grouped == {}
    assert not (tmp_path / "original" / "edgar").exists()

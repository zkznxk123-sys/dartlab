"""gather.original.edgar.submissions — 전 form 열거 + URL 구성 unit 테스트 (네트워크 0)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

_SUBMISSIONS = {
    "filings": {
        "recent": {
            "form": ["10-K", "8-K", "8-K"],
            "accessionNumber": [
                "0000320193-24-000001",
                "0000320193-24-000002",
                "0000320193-23-000050",
            ],
            "filingDate": ["2024-11-01", "2024-05-01", "2023-02-01"],
            "primaryDocument": ["aapl.htm", "8k1.htm", "8k2.htm"],
        },
        "files": [],
    }
}


def test_submissionTextUrl() -> None:
    """full submission .txt URL 구성 (accNoDash dir + accession.txt)."""
    from dartlab.gather.original.edgar.submissions import _submissionTextUrl

    url = _submissionTextUrl("0000320193", "0000320193-24-000001")
    assert url.endswith("/0000320193/000032019324000001/0000320193-24-000001.txt")


def test_listAllFilings_all_forms(monkeypatch: pytest.MonkeyPatch) -> None:
    """form 필터 없으면 전 form(10-K + 8-K) 반환 — sinceYear 로 옛 행 제외."""
    from dartlab.gather.original.edgar import submissions as sub

    monkeypatch.setattr(sub, "_getJson", lambda url: dict(_SUBMISSIONS))
    rows = sub.listAllFilings("0000320193", sinceYear=2024)
    forms = {r["form"] for r in rows}
    assert forms == {"10-K", "8-K"}  # 전 form
    assert all(r["year"] >= "2024" for r in rows)  # 2023 행 제외


def test_listAllFilings_form_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    """forms=['8-K'] 면 8-K 만 (정기 10-K 제외) — 비정기 수집 가능 증명."""
    from dartlab.gather.original.edgar import submissions as sub

    monkeypatch.setattr(sub, "_getJson", lambda url: dict(_SUBMISSIONS))
    rows = sub.listAllFilings("0000320193", sinceYear=2024, forms=["8-K"])
    assert len(rows) == 1
    assert rows[0]["form"] == "8-K"
    assert rows[0]["txt_url"].endswith(".txt")


def test_listAllFilings_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """limit 은 최신 N 건 tail (메모리 가드 룰 8)."""
    from dartlab.gather.original.edgar import submissions as sub

    monkeypatch.setattr(sub, "_getJson", lambda url: dict(_SUBMISSIONS))
    rows = sub.listAllFilings("0000320193", sinceYear=2009, limit=1)
    assert len(rows) == 1
    assert rows[0]["filing_date"] == "2024-11-01"  # 가장 최신

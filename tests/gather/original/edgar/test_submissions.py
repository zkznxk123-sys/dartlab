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


# --- resolveCik: company_tickers.json + browse-edgar fallback (네트워크 0) ---

_COMPANY_TICKERS = {
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
}


class _FakeResp:
    def __init__(self, status_code: int, text: str) -> None:
        self.status_code = status_code
        self.text = text


def _resetCikCaches(monkeypatch: pytest.MonkeyPatch, sub) -> None:
    """프로세스 캐시(_TICKER_MAP/_CIK_FALLBACK) 를 테스트마다 초기화 — 격리."""
    monkeypatch.setattr(sub, "_TICKER_MAP", None)
    monkeypatch.setattr(sub, "_CIK_FALLBACK", {})
    monkeypatch.setattr(sub, "_getJson", lambda url: dict(_COMPANY_TICKERS))


def test_resolveCik_company_tickers_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    """company_tickers.json 에 있으면 fast path — browse-edgar 미호출."""
    from dartlab.gather.original.edgar import submissions as sub

    _resetCikCaches(monkeypatch, sub)

    def _boom(*a, **k):  # browse-edgar 가 호출되면 실패
        raise AssertionError("browse-edgar fallback 이 불필요하게 호출됨")

    monkeypatch.setattr(sub.httpx, "get", _boom)
    assert sub.resolveCik("AAPL") == "0000320193"
    assert sub.resolveCik("aapl") == "0000320193"  # 대소문자 무관


def test_resolveCik_browse_edgar_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """company_tickers.json 누락(CTRA) → browse-edgar atom 에서 CIK 해소."""
    from dartlab.gather.original.edgar import submissions as sub

    _resetCikCaches(monkeypatch, sub)
    atom = "<feed><company-info><CIK=0000858470</company-info></feed>"

    calls = {"n": 0}

    def _fakeGet(url, **k):
        calls["n"] += 1
        assert "ticker=CTRA" in url  # browse-edgar 조회 ticker 전달 확인
        return _FakeResp(200, atom)

    monkeypatch.setattr(sub.httpx, "get", _fakeGet)
    assert sub.resolveCik("CTRA") == "0000858470"
    # 음성/양성 모두 캐시 — 재호출 시 네트워크 0
    assert sub.resolveCik("CTRA") == "0000858470"
    assert calls["n"] == 1


def test_resolveCik_unresolvable_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """company_tickers.json + browse-edgar 모두 miss → ValueError."""
    from dartlab.gather.original.edgar import submissions as sub

    _resetCikCaches(monkeypatch, sub)
    monkeypatch.setattr(sub.httpx, "get", lambda url, **k: _FakeResp(200, "<feed></feed>"))
    with pytest.raises(ValueError, match="찾을 수 없음"):
        sub.resolveCik("ZZZZQQ")


def test_resolveCik_numeric_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    """숫자 입력은 zfill(10) — 네트워크 0."""
    from dartlab.gather.original.edgar import submissions as sub

    _resetCikCaches(monkeypatch, sub)
    monkeypatch.setattr(sub.httpx, "get", lambda *a, **k: (_ for _ in ()).throw(AssertionError))
    assert sub.resolveCik("858470") == "0000858470"

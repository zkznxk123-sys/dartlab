"""gather.original.dart.client — OriginalDartClient 키풀/엔드포인트 unit 테스트 (네트워크 0)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


class _FakeResp:
    """httpx.Response 흉내 — status/headers/json/content 최소 surface."""

    def __init__(self, *, contentType="application/zip", content=b"", payload=None):
        self.headers = {"Content-Type": contentType}
        self.content = content
        self._payload = payload or {}

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_no_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """키 0개면 OriginalDartClientError."""
    from dartlab.gather.original.dart import client as clientMod

    monkeypatch.delenv("DART_API_KEY", raising=False)
    monkeypatch.delenv("DART_API_KEYS", raising=False)
    monkeypatch.setattr(clientMod, "resolveDartKeys", lambda **_: [])

    with pytest.raises(clientMod.OriginalDartClientError):
        clientMod.OriginalDartClient()


def test_acquire_slot_sequential_exhausted() -> None:
    """매 요청 동일 키(slot0) — cooldown 발생해야 다음 키(slot1) 전환 (§15 per-IP 회피)."""
    from dartlab.gather.original.dart.client import OriginalDartClient

    client = OriginalDartClient(apiKeys=["k1", "k2"])
    s1, _ = client._acquireSlot()
    client._releaseSlot(s1)
    s2, _ = client._acquireSlot()
    client._releaseSlot(s2)
    assert s1.key == "k1" and s2.key == "k1"  # 매 요청 rotation 아님

    client._markCoolDown(s1)  # slot0 한도 → cooldown
    s3, _ = client._acquireSlot()
    client._releaseSlot(s3)
    assert s3.key == "k2"  # 다음 키로 sequential 전환


def test_getBytes_returns_content(monkeypatch: pytest.MonkeyPatch) -> None:
    """getBytes 는 zip content 를 그대로 반환(content-type 비-json)."""
    from dartlab.gather.original.dart.client import OriginalDartClient

    client = OriginalDartClient(apiKey="k1")
    monkeypatch.setattr(
        client._session,
        "get",
        lambda *a, **k: _FakeResp(contentType="application/x-zip", content=b"PK\x03\x04zip"),
    )
    raw = client.getBytes("document.xml", {"rcept_no": "20240101000001"})
    assert raw == b"PK\x03\x04zip"


def test_getFilingsPage_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    """getFilingsPage 는 status 000 raw JSON 을 반환."""
    from dartlab.gather.original.dart.client import OriginalDartClient

    client = OriginalDartClient(apiKey="k1")
    payload = {"status": "000", "list": [{"rcept_no": "x"}], "total_page": 1}
    monkeypatch.setattr(
        client._session,
        "get",
        lambda *a, **k: _FakeResp(contentType="application/json", payload=payload),
    )
    data = client.getFilingsPage(bgnDe="20260601", endDe="20260601")
    assert data["status"] == "000" and data["list"][0]["rcept_no"] == "x"

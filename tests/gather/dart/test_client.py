"""gather/dart/client.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.gather.dart.client  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_get_bytes_callable() -> None:
    """getBytes() callable smoke."""
    from dartlab.gather.dart.client import DartClient

    assert hasattr(DartClient, "getBytes")


def test_get_df_callable() -> None:
    """getDf() callable smoke."""
    from dartlab.gather.dart.client import DartClient

    assert hasattr(DartClient, "getDf")


def test_get_df_all_callable() -> None:
    """getDfAll() callable smoke."""
    from dartlab.gather.dart.client import DartClient

    assert hasattr(DartClient, "getDfAll")


def test_get_json_callable() -> None:
    """getJson() callable smoke."""
    from dartlab.gather.dart.client import DartClient

    assert hasattr(DartClient, "getJson")


class _FakeJsonResp:
    status_code = 200
    headers = {"Content-Type": "application/json"}

    def raise_for_status(self) -> None:  # 2xx → no-op
        pass

    def json(self) -> dict:
        return {"status": "000", "ok": True}


def test_get_json_retries_transient_transport_error(monkeypatch) -> None:
    """getJson 은 전송 계층 일시 장애(RemoteProtocolError)를 재시도하고 회복한다.

    Original SSOT Sync dart-reconcile 가 DART 서버 연결 끊김 한 번에 잡 전체가 죽던 갭의 회귀 가드.
    """
    import httpx

    from dartlab.gather.dart import client as client_mod

    monkeypatch.setattr(client_mod.time, "sleep", lambda *_a, **_k: None)  # 백오프 즉시
    c = client_mod.DartClient(apiKey="DUMMY")

    calls = {"n": 0}

    def fake_get(url, params=None, timeout=None):
        calls["n"] += 1
        if calls["n"] < 3:
            raise httpx.RemoteProtocolError("Server disconnected without sending a response.")
        return _FakeJsonResp()

    monkeypatch.setattr(c._session, "get", fake_get)
    out = c.getJson("list.json", params={})
    assert out["status"] == "000"
    assert calls["n"] == 3  # 2회 끊김 후 3회차 성공


def test_get_json_raises_after_transient_retries_exhausted(monkeypatch) -> None:
    """재시도 소진 시 마지막 전송 예외를 그대로 올린다(무한 재시도·조용한 삼킴 아님)."""
    import httpx

    from dartlab.gather.dart import client as client_mod

    monkeypatch.setattr(client_mod.time, "sleep", lambda *_a, **_k: None)
    c = client_mod.DartClient(apiKey="DUMMY")

    def always_disconnect(url, params=None, timeout=None):
        raise httpx.RemoteProtocolError("Server disconnected without sending a response.")

    monkeypatch.setattr(c._session, "get", always_disconnect)
    with pytest.raises(httpx.RemoteProtocolError):
        c.getJson("list.json", params={})

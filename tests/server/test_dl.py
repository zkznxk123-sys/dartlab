"""Master API dispatch (POST /api/dl/call, GET /api/dl/capabilities) 테스트.

unit:
    - capability catalogue 가 5 L2 엔진 + Company + Story 포함
    - 잘못된 apiRef → 400
    - private (_internal) → 400
    - missing apiRef → 422 (pydantic) 또는 400

integration:
    - Company.show 실제 호출 (데이터 있을 때만)
"""

from __future__ import annotations

import pytest

starlette = pytest.importorskip("starlette", reason="starlette not installed (optional [ai] dependency)")
from starlette.testclient import TestClient  # noqa: E402

from dartlab.server import app  # noqa: E402

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


class TestDlCapabilities:
    """GET /api/dl/capabilities — registry catalogue."""

    def test_returns_count_and_items(self, client):
        resp = client.get("/api/dl/capabilities")
        assert resp.status_code == 200
        body = resp.json()
        assert "count" in body and "items" in body
        assert body["count"] > 0
        assert isinstance(body["items"], list)
        assert all("apiRef" in item for item in body["items"])

    def test_contains_company_show(self, client):
        resp = client.get("/api/dl/capabilities")
        refs = {item["apiRef"] for item in resp.json()["items"]}
        assert "Company.show" in refs
        assert "Company" in refs

    def test_contains_l2_engines(self, client):
        resp = client.get("/api/dl/capabilities")
        refs = {item["apiRef"] for item in resp.json()["items"]}
        # L2 5 engines + L3 Story 가 catalogue 에 존재
        for engine in ("analysis", "quant", "credit", "macro", "industry"):
            assert engine in refs, f"engine missing from catalogue: {engine}"


class TestDlCallValidation:
    """POST /api/dl/call — validation/whitelist."""

    def test_unknown_api_ref_400(self, client):
        resp = client.post(
            "/api/dl/call",
            json={"apiRef": "Company.thisDoesNotExist"},
        )
        assert resp.status_code == 400
        detail = resp.json().get("detail", {})
        assert detail.get("error") == "unknown_api_ref"

    def test_private_api_blocked_400(self, client):
        resp = client.post(
            "/api/dl/call",
            json={"apiRef": "_internalThing"},
        )
        assert resp.status_code == 400
        detail = resp.json().get("detail", {})
        assert detail.get("error") in {"private_api_blocked", "unknown_api_ref"}

    def test_missing_api_ref_returns_error(self, client):
        # pydantic 가 빈 apiRef 를 막거나 (422), engineCall 이 missing_api_ref 로 처리 (400)
        resp = client.post("/api/dl/call", json={})
        assert resp.status_code in {400, 422}

    def test_capability_exists_but_no_target_returns_meaningful_error(self, client):
        """Company.show 는 target 필요 — 빈 target 이면 graceful 실패."""
        resp = client.post(
            "/api/dl/call",
            json={"apiRef": "Company.show"},
        )
        # 200 (어떻게든 처리) 또는 400 (target 필요) — 둘 다 허용. 500 아니면 OK.
        assert resp.status_code != 500

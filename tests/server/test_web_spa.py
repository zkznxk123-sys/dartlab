"""SPA 정적 서빙 테스트 — React(assets/) ↔ SvelteKit(_app/) 양 번들 구조 회귀 가드.

단계-10 wheel 전환(pip 번들 UI = ui/apps/local SvelteKit, @dartlab/ui-surfaces 공유 소비)으로
번들 자산 경로가 assets/ → _app/ 로 바뀌었다. 옛 registerSpa 는 assets/ 를 무조건 StaticFiles
mount 해서 Svelte 번들(assets/ 부재)에선 서버 startup 이 RuntimeError 로 죽는 잠재 버그가 있었다
(SPA 서빙 테스트 커버리지 0 이라 컴파일·빌드 게이트가 못 잡는 런타임 사각). 본 테스트는 두 구조
모두에서 ① registerSpa 등록 무크래시 ② index/자산/SPA fallback/누락 404 서빙을 고정한다.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

pytestmark = pytest.mark.unit


def _mkbuild(tmp_path: Path, *, react: bool) -> Path:
    """가짜 UI 빌드 디렉토리 — react=True 면 assets/(ui/web), False 면 _app/(ui/apps/local)."""
    build = tmp_path / "build"
    build.mkdir()
    (build / "index.html").write_text("<!doctype html><html><body>dartlab</body></html>", encoding="utf-8")
    if react:
        (build / "assets").mkdir()
        (build / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    else:
        appdir = build / "_app" / "immutable" / "chunks"
        appdir.mkdir(parents=True)
        (appdir / "entry.js").write_text("export const x = 1", encoding="utf-8")
    return build


def _client(monkeypatch, build: Path) -> TestClient:
    import dartlab.server.web as web

    monkeypatch.setattr(web, "_UI_DIR", build)
    app = FastAPI()
    web.registerSpa(app)  # assets/ 부재 구조에서도 RuntimeError 없이 등록돼야 한다
    return TestClient(app)


def test_svelte_bundle_serves(tmp_path, monkeypatch):
    """SvelteKit 번들(_app/, assets/ 부재) — 등록 무크래시 + _app 자산 + SPA fallback."""
    client = _client(monkeypatch, _mkbuild(tmp_path, react=False))

    assert client.get("/").status_code == 200
    asset = client.get("/_app/immutable/chunks/entry.js")
    assert asset.status_code == 200
    assert "javascript" in asset.headers.get("content-type", "")
    assert client.get("/terminal/005930").status_code == 200  # SPA fallback → index.html
    assert client.get("/_app/missing-xyz.js").status_code == 404  # 누락 js = 404 (stale 캐시 차단)


def test_react_bundle_serves(tmp_path, monkeypatch):
    """assets/ 번들 구조 방어 — registerSpa 가 assets/ 레이아웃도 무크래시 서빙(옛 React 호환, ui/web 회수 후 현재 미사용이나 방어 유지). debt-honesty P2-2."""
    client = _client(monkeypatch, _mkbuild(tmp_path, react=True))

    assert client.get("/").status_code == 200
    assert client.get("/assets/app.js").status_code == 200
    assert client.get("/analysis/005930").status_code == 200  # SPA fallback → index.html

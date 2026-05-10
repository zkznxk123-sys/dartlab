"""Web/static helpers for the embedded Svelte UI."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from ._ui_path import resolveUiBuildDir

_UI_DIR = resolveUiBuildDir()


def registerSpa(app: FastAPI) -> None:
    """Svelte SPA 정적 파일 서빙과 fallback 라우트를 등록한다."""
    if _UI_DIR.exists():
        app.mount("/assets", StaticFiles(directory=str(_UI_DIR / "assets")), name="assets")
    app.add_api_route("/{path:path}", serveSpa, methods=["GET"])


def serveSpa(path: str = ""):
    """SPA fallback — index.html 반환."""
    if not _UI_DIR.exists():
        return HTMLResponse(
            "<h2>DartLab UI를 사용할 수 없습니다</h2>"
            "<p><code>pip install dartlab</code>을 최신 버전으로 업그레이드하세요:</p>"
            "<pre>pip install --upgrade dartlab</pre>"
            "<p>또는 CLI에서 바로 사용하세요: <code>dartlab ask '삼성전자 분석해줘'</code></p>",
            status_code=503,
        )

    file = _UI_DIR / path
    if path and file.is_file():
        try:
            file.resolve().relative_to(_UI_DIR.resolve())
        except ValueError:
            return HTMLResponse("Not found", status_code=404)
        return FileResponse(file)

    # 옛 hash bundle 요청을 index.html로 fallback하면 폰 Chrome이 옛 캐시를 영원히 들고 있음.
    # 존재하지 않는 /assets/* 는 명시적으로 404로 응답해야 캐시가 무효화됨.
    if path.startswith("assets/") or path.endswith((".js", ".css", ".map")):
        return HTMLResponse("Not found", status_code=404)

    index = _UI_DIR / "index.html"
    if index.exists():
        return FileResponse(
            index,
            media_type="text/html",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate, max-age=0"},
        )

    return HTMLResponse("<h2>index.html not found</h2>", status_code=404)

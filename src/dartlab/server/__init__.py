"""DartLab Web Server — FastAPI + SSE 스트리밍.

dartlab ai 명령으로 실행:
    dartlab ai              # http://localhost:8400
    dartlab ai --port 9000  # 커스텀 포트
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

import dartlab
from dartlab.ai.runtime.progressCapture import installProgressCapture
from dartlab.core.logger import getLogger as _bootstrapLogger

from .api import (
    ai_router,
    analysis_router,
    ask_router,
    company_router,
    dart_router,
    data_router,
    macro_router,
    room_router,
)
from .embed import router as embed_router
from .runtime import ensure_port, run_server  # noqa: F401 — re-exported
from .services.ai_profile import should_preload_ollama as _should_preload_ollama
from .web import register_spa

logger = logging.getLogger(__name__)


async def _preload_ollama_once() -> None:
    """서버 시작 직후 Ollama 모델을 미리 깨워 cold start를 줄인다."""

    await asyncio.sleep(2)

    try:
        from dartlab.ai import get_config
        from dartlab.ai.providers import create_provider

        config = get_config("ollama")
        provider = create_provider(config)
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        logger.debug("Ollama preload 준비 실패", exc_info=exc)
        return

    if not hasattr(provider, "preload"):
        return

    try:
        if provider.check_available():
            ok = await asyncio.to_thread(provider.preload)
            if ok:
                logger.info("Ollama 모델 preload 완료: %s", provider.resolved_model)
    except (ConnectionError, OSError, RuntimeError, TimeoutError, ValueError) as exc:
        logger.debug("Ollama preload 실행 실패", exc_info=exc)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """앱 수명주기 관리 -- Ollama preload, 룸 생성/정리, 채널 종료."""
    preload_task = asyncio.create_task(_preload_ollama_once()) if _should_preload_ollama() else None

    # 채널 모드: 협업 룸 자동 생성 + 백그라운드 정리
    from .room import room_manager

    if os.environ.get("DARTLAB_CHANNEL") == "1":
        room_manager.create_room()
        room_manager.start_background_cleanup()

    try:
        yield
    finally:
        from .services.channel_runtime import channel_runtime
        from .services.dev_channel_runtime import dev_channel_runtime

        dev_channel_runtime.shutdown()
        channel_runtime.shutdown_all()
        room_manager.stop_background_cleanup()
        room_manager.destroy_room()

        if preload_task is not None and not preload_task.done():
            preload_task.cancel()
        with suppress(asyncio.CancelledError):
            if preload_task is not None:
                await preload_task


# dartlab logger 초기화 후 tool 진행 라인을 SSE 로 흘리기 위한 capture 설치.
# idempotent — 여러 worker / reload 시 안전.
_bootstrapLogger()
installProgressCapture()

app = FastAPI(title="DartLab", version=dartlab.__version__, lifespan=lifespan)


def _cors_origins() -> list[str]:
    raw = os.environ.get("DARTLAB_CORS_ORIGINS")
    if raw:
        raw = raw.strip()
        if raw == "*":
            return ["*"]
        return [item.strip() for item in raw.split(",") if item.strip()]
    # devtunnel 모드 등 외부 접근 시 CORS가 막혀서 fetch hang — 터널 모드면 전체 허용
    if os.environ.get("DARTLAB_CHANNEL") == "1" or os.environ.get("DARTLAB_TUNNEL") == "1":
        return ["*"]
    return [
        "http://127.0.0.1:8400",
        "http://localhost:8400",
        "http://127.0.0.1:5400",
        "http://localhost:5400",
    ]


class _SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        """보안 헤더(X-Content-Type-Options 등)를 모든 응답에 추가한다."""
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response


app.add_middleware(_SecurityHeadersMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=500)

_origins = _cors_origins()
if _origins == ["*"]:
    logger.warning("CORS allow_origins='*' — 프로덕션에서는 명시적 origin을 설정하세요")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Room-Member", "X-Tunnel-Skip-AntiPhishing-Page-Redirect", "*"],
)

app.include_router(ai_router)
app.include_router(analysis_router)
app.include_router(ask_router)
app.include_router(company_router)
app.include_router(data_router)
app.include_router(macro_router)
app.include_router(room_router)
app.include_router(dart_router)
app.include_router(embed_router)

# ── MCP SSE 마운트 (HF Spaces 또는 명시적 활성화 시) ──
if os.environ.get("SPACE_ID") or os.environ.get("DARTLAB_MCP_HTTP") == "1":
    try:
        from dartlab.mcp import create_sse_app

        _mcp_sse = create_sse_app()
        app.mount("/mcp", _mcp_sse)
        logger.info("MCP SSE 엔드포인트 활성화: /mcp/sse")
    except ImportError:
        logger.info("MCP SDK 미설치 — MCP SSE 비활성")

register_spa(app)

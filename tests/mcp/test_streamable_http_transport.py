"""Streamable HTTP transport 단위 — 마스터 플랜 v2 트랙 7 PR-M4.

createStreamableHttpApp + CLI argparse 단위. uvicorn 실행 0 (network 0).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_createStreamableHttpApp_importable() -> None:
    """함수 noop import — Streamable HTTP transport 의존성 누락 0."""
    from dartlab.mcp.transports import createStreamableHttpApp

    assert callable(createStreamableHttpApp)


def test_createStreamableHttpApp_returns_starlette_app() -> None:
    """app instance 가 Starlette 의 routes / lifespan 보유."""
    pytest.importorskip("mcp.server.streamable_http_manager")
    from dartlab.mcp.transports import createStreamableHttpApp

    app = createStreamableHttpApp()
    # Starlette app 은 routes 속성 보유
    assert hasattr(app, "routes")
    # /mcp 경로 단일 mount
    paths = [getattr(r, "path", None) for r in app.routes]
    assert "/mcp" in paths or any(p and p.startswith("/mcp") for p in paths if p)


def test_createStreamableHttpApp_json_response_mode() -> None:
    pytest.importorskip("mcp.server.streamable_http_manager")
    from dartlab.mcp.transports import createStreamableHttpApp

    app = createStreamableHttpApp(jsonResponse=True)
    assert app is not None


def test_runStreamableHttp_signature() -> None:
    """runStreamableHttp 함수 signature 가 host/port/jsonResponse 받음."""
    import inspect

    from dartlab.mcp.transports import runStreamableHttp

    sig = inspect.signature(runStreamableHttp)
    params = list(sig.parameters)
    assert "host" in params
    assert "port" in params
    assert "jsonResponse" in params


def test_mcp_main_argparse_http_transport() -> None:
    """python -m dartlab.mcp --transport http → http 선택."""
    from dartlab.mcp.__main__ import _parseArgs

    args = _parseArgs(["--transport", "http", "--port", "8002"])
    assert args.transport == "http"
    assert args.port == 8002


def test_mcp_main_argparse_default_stdio() -> None:
    """기본은 stdio 유지 (회귀 가드)."""
    from dartlab.mcp.__main__ import _parseArgs

    args = _parseArgs([])
    assert args.transport == "stdio"


def test_mcp_main_argparse_sse_legacy() -> None:
    from dartlab.mcp.__main__ import _parseArgs

    args = _parseArgs(["--transport", "sse"])
    assert args.transport == "sse"


def test_mcp_main_argparse_json_response_flag() -> None:
    from dartlab.mcp.__main__ import _parseArgs

    args = _parseArgs(["--transport", "http", "--json-response"])
    assert args.json_response is True


def test_mcp_init_exposes_streamable_http() -> None:
    """__init__.py 가 createStreamableHttpApp + runStreamableHttp 공개."""
    import dartlab.mcp as m

    assert hasattr(m, "createStreamableHttpApp")
    assert hasattr(m, "runStreamableHttp")
    assert "createStreamableHttpApp" in m.__all__
    assert "runStreamableHttp" in m.__all__

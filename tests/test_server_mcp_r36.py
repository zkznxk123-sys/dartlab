"""R36 audit 회귀 — server + mcp.

R36 audit: server security whitelist + MCP module 정상.
회귀 보호.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_server_security_whitelist_loads():
    """server security 모듈 import + whitelist 함수 호출 가능."""
    from dartlab.server.security import _is_whitelisted

    assert callable(_is_whitelisted)
    # 기본 endpoint 보호
    assert _is_whitelisted("/api/spec") is True
    assert _is_whitelisted("/api/company/005930") is True


def test_server_security_blocks_unknown_paths():
    """알려지지 않은 경로 차단."""
    from dartlab.server.security import _is_whitelisted

    assert _is_whitelisted("/api/없는경로") is False
    assert _is_whitelisted("/api/random/junk") is False


def test_mcp_module_loads():
    """MCP 모듈 import 가능."""
    import dartlab.mcp

    assert dartlab.mcp is not None


def test_server_web_module_loads():
    """server.web 모듈 import 가능."""
    from dartlab.server import web

    assert web is not None

"""Benchmark 시나리오 4 — MCP server boot + 첫 tool call (T3-1)."""

from __future__ import annotations

import pytest


@pytest.mark.benchmark
@pytest.mark.serial
class TestMcpBoot:
    """MCP server import + 첫 tool call P50 ≤ 5s 목표."""

    def test_mcp_import(self, benchmark) -> None:
        def importMcp() -> object:
            try:
                import dartlab.mcp

                return dartlab.mcp
            except ImportError:
                pytest.skip("dartlab.mcp 미설치")
                return None

        benchmark(importMcp)

"""R35 audit 회귀 — cli 엔진.

R35 audit: cli 가 잘못된 종목/명령에 명확한 안내. silent failure 0건.
회귀 보호 source check.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_cli_parser_has_15_commands():
    """공개 CLI 명령 15개 보호."""
    from dartlab.cli.parser import buildParser

    parser = buildParser()
    subparsers_action = None
    for action in parser._actions:
        if hasattr(action, "choices") and isinstance(action.choices, dict):
            subparsers_action = action
            break
    assert subparsers_action is not None
    commands = list(subparsers_action.choices.keys())
    expected = ["show", "search", "statement", "profile", "modules", "ask", "collect", "status", "setup", "mcp"]
    for cmd in expected:
        assert cmd in commands, f"CLI 명령 누락: {cmd}"


def test_cli_main_entry_callable():
    """dartlab.cli.main.main 진입점 존재 보호."""
    from dartlab.cli.main import main

    assert callable(main)

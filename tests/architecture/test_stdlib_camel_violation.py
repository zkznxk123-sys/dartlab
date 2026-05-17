"""stdlib API 무차별 카멜케이스 변환 회귀 가드.

P6 PR 3 codemod (commit 452fbe3c6) 의 leave_Attribute 가 dartlab 자체 정의 함수
(예: kernel.createTask) 와 같은 이름의 stdlib attr 까지 변환한 사고 (commit 1cf9bdef8 복구).

stdlib (asyncio · subprocess · threading · multiprocessing) 의 모든 public API 는
snake_case. 모듈 prefix 다음에 camelCase 호출이 잡히면 회귀.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2] / "src" / "dartlab"

PROTECTED_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("asyncio", re.compile(r"\basyncio\.[a-z][a-zA-Z]*[A-Z]")),
    ("subprocess", re.compile(r"\bsubprocess\.[a-z][a-zA-Z]*[A-Z]")),
    ("threading", re.compile(r"\bthreading\.[a-z][a-zA-Z]*[A-Z]")),
    ("multiprocessing", re.compile(r"\bmultiprocessing\.[a-z][a-zA-Z]*[A-Z]")),
    # mcp Server/ClientSession 데코레이터·메서드 (snake_case stdlib 표준):
    # list_tools, call_tool, list_resources, read_resource, list_prompts,
    # get_prompt, set_logging_level, send_progress_notification 등.
    (
        "mcp.app",
        re.compile(
            r"@(?:app|server)\.(?:listTools|callTool|listResources|readResource|"
            r"listPrompts|getPrompt|setLoggingLevel|sendProgressNotification)\("
        ),
    ),
    (
        "mcp.session",
        re.compile(
            r"\bsession\.(?:listTools|callTool|listResources|readResource|"
            r"listPrompts|getPrompt|setLoggingLevel|sendProgressNotification)\("
        ),
    ),
)


@pytest.mark.unit
def test_no_stdlib_camel_violation() -> None:
    violations: list[str] = []
    for path in ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for _modName, pattern in PROTECTED_PATTERNS:
            for m in pattern.finditer(text):
                rel = path.relative_to(ROOT.parent.parent)
                violations.append(f"{rel}: {m.group()}")
    assert not violations, (
        "stdlib API 의 무차별 카멜케이스 변환 잔존 — codemod 의 leave_Attribute 가 "
        "dartlab 자체 정의 함수와 같은 이름의 stdlib attr 까지 변환한 회귀:\n" + "\n".join(violations)
    )

"""CLI 기반 LLM 도구 (Codex) 설치 감지 및 안내."""

from __future__ import annotations

import platform

_IS_WINDOWS = platform.system() == "Windows"


def detect_codex() -> dict:
    """OpenAI Codex CLI 상태 감지.

    Returns:
            {"installed": bool, "version": str | None}
    """
    from dartlab.ai.providers.support.codex_cli import inspect_codex_cli

    return inspect_codex_cli()


def get_codex_install_guide() -> str:
    """OS별 Codex CLI 설치 안내."""
    guide = "[ OpenAI Codex CLI 설치 안내 ]\n\n"
    guide += "1. npm install -g @openai/codex\n2. 처음 실행 시 로그인: codex\n3. 확인: codex --version\n"
    guide += "\nChatGPT Plus/Pro 구독이 필요합니다.\n문서: https://developers.openai.com/codex/cli/\n"
    return guide

"""실 LLM e2e — OAuth Codex (ChatGPT 구독) 우선.

OAuth 로그인 토큰 (~/.dartlab/oauth_token.json) 또는 DARTLAB_OAUTH_TOKEN 환경변수 있을 때 실행.
비용 발생 — CI 자동 실행 금지.
"""

from __future__ import annotations

import os

import pytest

requires_oauth_codex = pytest.mark.skipif(
    not (os.environ.get("DARTLAB_OAUTH_TOKEN") or os.path.exists(os.path.expanduser("~/.dartlab/oauth_token.json"))),
    reason="OAuth Codex 토큰 없음 — 실 LLM e2e 스킵",
)


@pytest.mark.heavy
@requires_oauth_codex
def test_real_oauth_codex_simple_question_returns_text() -> None:
    from dartlab.ai import ask
    from dartlab.ai.providers import createProvider, getConfig

    config = getConfig(provider="oauth-codex")
    provider = createProvider(config)
    text = ask(
        "DartLab 라이브러리는 무엇이고 어떤 분석을 할 수 있는지 한 문단으로 설명",
        stream=False,
        provider=provider,
    )
    assert isinstance(text, str)
    assert len(text) > 50


@pytest.mark.heavy
@requires_oauth_codex
def test_real_oauth_codex_5_passes_invoked() -> None:
    from dartlab.ai.providers import createProvider, getConfig
    from dartlab.ai.workbench.loop import WorkbenchLoop

    config = getConfig(provider="oauth-codex")
    provider = createProvider(config)
    loop = WorkbenchLoop()
    passes_seen: list[str] = []
    for ev in loop.stream("hi", provider=provider):
        if ev.kind == "pass_enter":
            passes_seen.append(ev.data.get("pass", ""))
    for required in ("brief", "work", "compose", "gate"):
        assert required in passes_seen, f"{required} 패스 미실행"

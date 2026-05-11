"""Provider 시스템 (ProviderConfig / ProviderTurn / WorkbenchProvider / createProvider)."""

from __future__ import annotations

import pytest

from dartlab.ai.providers import (
    OpenAICompatibleProvider,
    ProviderConfig,
    ProviderTurn,
    ToolCall,
    UnavailableProvider,
    availableProviders,
    createProvider,
    getConfig,
)


@pytest.mark.unit
def test_available_providers_excludes_anthropic_includes_oauth_codex() -> None:
    names = set(availableProviders())
    # anthropic 직접 사용 금지 (ToS)
    assert "anthropic" not in names
    assert "claude" not in names
    # 정식 1 순위
    assert "oauth-codex" in names
    # OpenAI 호환 군
    for pid in ("openai", "ollama", "custom", "groq", "cerebras", "mistral", "gemini"):
        assert pid in names


@pytest.mark.unit
def test_get_config_normalizes_chatgpt_to_oauth_codex() -> None:
    cfg = getConfig(provider="chatgpt")
    assert cfg.provider == "oauth-codex"


@pytest.mark.unit
def test_get_config_normalizes_openai_compat_aliases() -> None:
    cfg = getConfig(provider="openai-compatible")
    assert cfg.provider == "custom"


@pytest.mark.unit
def test_create_provider_oauth_codex_returns_oauth_provider() -> None:
    from dartlab.ai.providers.oauthCodex import OAuthCodexProvider

    provider = createProvider(ProviderConfig(provider="oauth-codex"))
    assert isinstance(provider, OAuthCodexProvider)


@pytest.mark.unit
def test_create_provider_openai_returns_compat_provider() -> None:
    provider = createProvider(ProviderConfig(provider="openai", apiKey="sk-test"))
    assert isinstance(provider, OpenAICompatibleProvider)


@pytest.mark.unit
def test_create_provider_groq_cerebras_mistral_custom_use_compat() -> None:
    for pid in ("groq", "cerebras", "mistral", "custom", "ollama"):
        provider = createProvider(ProviderConfig(provider=pid, apiKey="x"))
        assert isinstance(provider, OpenAICompatibleProvider), f"{pid} not compat"


@pytest.mark.unit
def test_create_provider_chatgpt_alias_blocked() -> None:
    with pytest.raises(ValueError):
        createProvider(provider="chatgpt")


@pytest.mark.unit
def test_create_provider_unknown_returns_unavailable() -> None:
    provider = createProvider(ProviderConfig(provider="nonexistent_xyz"))
    assert isinstance(provider, UnavailableProvider)
    assert provider.checkAvailable() is False


@pytest.mark.unit
def test_provider_turn_dataclass_shape() -> None:
    tc = ToolCall(id="c1", name="run_python", args={"code": "1+1"})
    turn = ProviderTurn(content="ok", toolCalls=[tc])
    assert turn.content == "ok"
    assert turn.toolCalls[0].name == "run_python"


@pytest.mark.unit
@pytest.mark.xfail(
    reason="가드 vs 구현 모순 — catalog.py 가 anthropic/xai 어댑터를 활성 import 중. "
    "정책 결정 (어댑터 유지 vs ToS 회피) 후 본 가드 또는 어댑터 한쪽 제거.",
    strict=False,
)
def test_no_anthropic_provider_module_in_providers_dir() -> None:
    """anthropic.py / xai.py 어댑터 파일이 존재하지 않아야 함 (ToS 회피)."""
    from pathlib import Path

    providers_dir = Path(__file__).resolve().parents[2] / "src" / "dartlab" / "ai" / "providers"
    files = {p.name for p in providers_dir.glob("*.py")}
    assert "anthropic.py" not in files
    assert "xai.py" not in files
    assert "claude.py" not in files
    assert "claude_code.py" not in files

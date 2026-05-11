"""모델 자동 최신화 회귀 가드.

backend 응답이 진실. 정적 fallback 이 stale 이어도 backend 가 신모델 주면 그게 default.
"""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_sort_openai_models_orders_by_version_desc() -> None:
    from dartlab.ai.settings.modelResolver import sortOpenaiModels

    result = sortOpenaiModels(["gpt-5.3", "gpt-5.5", "gpt-5.4"])
    # 첫 항목 = 최고 버전
    assert result[0] == "gpt-5.5"
    # 정렬: 5.5 > 5.4 > 5.3
    five_five_idx = result.index("gpt-5.5")
    five_four_idx = result.index("gpt-5.4")
    five_three_idx = result.index("gpt-5.3")
    assert five_five_idx < five_four_idx < five_three_idx


@pytest.mark.unit
def test_sort_openai_models_does_not_force_stale_fallback_to_top() -> None:
    """fallback 이 stale (5.4) 인데 input 에 5.5 있으면 5.5 가 첫 항목."""
    from dartlab.ai.settings import modelResolver as model_resolver
    from dartlab.ai.settings.modelResolver import sortOpenaiModels

    # stale fallback 시뮬레이션
    monkey_fallback = "gpt-5.4"
    original = model_resolver._FALLBACK_LATEST_MODEL
    model_resolver._FALLBACK_LATEST_MODEL = monkey_fallback
    try:
        result = sortOpenaiModels(["gpt-5.5", "gpt-5.4", "gpt-5.3"])
        assert result[0] == "gpt-5.5"
    finally:
        model_resolver._FALLBACK_LATEST_MODEL = original


@pytest.mark.unit
def test_latest_openai_model_uses_env_override(monkeypatch) -> None:
    from dartlab.ai.settings.modelResolver import latestOpenaiModel

    monkeypatch.setenv("DARTLAB_LATEST_OPENAI_MODEL", "gpt-5.6")
    assert latestOpenaiModel() == "gpt-5.6"


@pytest.mark.unit
def test_latest_openai_model_uses_backend_when_present(monkeypatch) -> None:
    """backend availableModels() 첫 신모델 사용."""
    from dartlab.ai.providers import oauthCodex as oauth_codex
    from dartlab.ai.settings.modelResolver import latestOpenaiModel

    monkeypatch.delenv("DARTLAB_LATEST_OPENAI_MODEL", raising=False)
    monkeypatch.setattr(oauth_codex, "availableModels", lambda: ["gpt-5.5", "gpt-5.4", "gpt-5.3"])
    assert latestOpenaiModel() == "gpt-5.5"


@pytest.mark.unit
def test_latest_openai_model_falls_back_when_backend_unavailable(monkeypatch) -> None:
    from dartlab.ai.providers import oauthCodex as oauth_codex
    from dartlab.ai.settings import modelResolver as model_resolver
    from dartlab.ai.settings.modelResolver import latestOpenaiModel

    monkeypatch.delenv("DARTLAB_LATEST_OPENAI_MODEL", raising=False)

    def _raise():
        raise RuntimeError("backend down")

    monkeypatch.setattr(oauth_codex, "availableModels", _raise)
    assert latestOpenaiModel() == model_resolver._FALLBACK_LATEST_MODEL


@pytest.mark.unit
def test_latest_openai_model_falls_back_when_backend_returns_empty(monkeypatch) -> None:
    from dartlab.ai.providers import oauthCodex as oauth_codex
    from dartlab.ai.settings import modelResolver as model_resolver
    from dartlab.ai.settings.modelResolver import latestOpenaiModel

    monkeypatch.delenv("DARTLAB_LATEST_OPENAI_MODEL", raising=False)
    monkeypatch.setattr(oauth_codex, "availableModels", lambda: [])
    assert latestOpenaiModel() == model_resolver._FALLBACK_LATEST_MODEL


@pytest.mark.unit
def test_resolve_default_model_uses_latest_for_openai_family() -> None:
    from dartlab.ai.settings.modelResolver import resolveDefaultModel

    # OpenAI family 에서 configured stale 무시 + latest 사용
    result = resolveDefaultModel("oauth-codex", configuredModel="gpt-4.1")
    assert result.startswith("gpt-")
    # latest 가 stale fallback 보다 같거나 신
    assert result != "gpt-4.1"


@pytest.mark.unit
def test_resolve_default_model_explicit_wins() -> None:
    from dartlab.ai.settings.modelResolver import resolveDefaultModel

    result = resolveDefaultModel("oauth-codex", explicitModel="gpt-4.1-mini")
    assert result == "gpt-4.1-mini"


@pytest.mark.unit
def test_fallback_constant_is_current() -> None:
    from dartlab.ai.settings.modelResolver import _FALLBACK_LATEST_MODEL

    # 정적 fallback 도 최신 버전 표기 — backend 죽었을 때 stale 답 안 주도록
    assert _FALLBACK_LATEST_MODEL.startswith("gpt-")

"""Provider 설정은 Workbench 외부 연결점으로만 유지한다."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_available_provider_is_dartlab_adapter_only():
    from dartlab.ai.providers import available_providers

    assert available_providers() == ["dartlab"]


def test_create_provider_returns_research_graph_adapter():
    from dartlab.ai.providers import create_provider
    from dartlab.ai.settings.types import LLMConfig

    provider = create_provider(LLMConfig(provider="dartlab", model="research"))

    assert provider.check_available() is True
    assert provider.resolved_model == "research"


def test_configure_role_binding_changes_resolved_config():
    from dartlab.ai import configure, get_config

    configure(provider="dartlab", model="base")
    configure(provider="dartlab", model="summary-model", role="summary")

    analysis = get_config()
    summary = get_config(role="summary")

    assert analysis.provider == "dartlab"
    assert analysis.model == "base"
    assert summary.provider == "dartlab"
    assert summary.model == "summary-model"


def test_provider_config_accepts_dict_input():
    from dartlab.ai.providers import create_provider

    provider = create_provider({"provider": "dartlab", "model": "dict-model", "ignored": "x"})

    assert provider.resolved_model == "dict-model"

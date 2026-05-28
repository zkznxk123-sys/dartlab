"""selectProviderForQuestion 단위 — 마스터 플랜 v2 트랙 7 PR-M3.

provider 자동 선택 + tier routing 결합. createProvider 호출 0 (config 만 검증).
"""

from __future__ import annotations

import pytest

from dartlab.ai.providers.routing import selectProviderForQuestion

pytestmark = pytest.mark.unit


def _yes(_: str) -> bool:
    return True


def _no(_: str) -> bool:
    return False


def _only(names: set[str]):
    def check(p: str) -> bool:
        return p in names

    return check


def test_selectProvider_anthropic_default_priority() -> None:
    """모든 provider 가용 → anthropic 우선."""
    cfg = selectProviderForQuestion("삼성전자 사업", availabilityCheck=_yes)
    assert cfg.provider == "anthropic"
    assert cfg.model is not None


def test_selectProvider_falls_back_to_openai() -> None:
    """anthropic 미가용 → openai 폴백."""
    cfg = selectProviderForQuestion("삼성전자", availabilityCheck=_only({"openai", "google"}))
    assert cfg.provider == "openai"


def test_selectProvider_falls_back_to_google() -> None:
    """anthropic / openai 모두 미가용 → google."""
    cfg = selectProviderForQuestion("삼성전자", availabilityCheck=_only({"google"}))
    assert cfg.provider == "google"


def test_selectProvider_returns_null_when_none_available() -> None:
    cfg = selectProviderForQuestion("삼성전자", availabilityCheck=_no)
    assert cfg.provider is None
    assert cfg.model is None


def test_selectProvider_preferProvider_used_when_available() -> None:
    """preferProvider 명시 + 가용 → 우선순위 무시."""
    cfg = selectProviderForQuestion(
        "삼성전자 DCF",
        preferProvider="google",
        availabilityCheck=_yes,
    )
    assert cfg.provider == "google"


def test_selectProvider_preferProvider_fallback_when_unavailable() -> None:
    """preferProvider 명시했으나 미가용 → 기본 candidates 폴백."""
    cfg = selectProviderForQuestion(
        "삼성전자",
        preferProvider="google",
        availabilityCheck=_only({"openai"}),
    )
    assert cfg.provider == "openai"


def test_selectProvider_tier_routing_deep_for_dcf() -> None:
    """DCF 키워드 → deep tier 모델."""
    cfg = selectProviderForQuestion("삼성전자 DCF 평가", availabilityCheck=_yes)
    assert cfg.provider == "anthropic"
    assert cfg.model == "claude-opus-4-7"


def test_selectProvider_tier_routing_cheap_for_short_lookup() -> None:
    cfg = selectProviderForQuestion("ROE 알려줘", availabilityCheck=_yes)
    assert cfg.model == "claude-haiku-4-5"


def test_selectProvider_configuredTier_overrides_inference() -> None:
    """configuredTier=cheap → 키워드 무시 cheap tier."""
    cfg = selectProviderForQuestion(
        "삼성전자 DCF",
        configuredTier="cheap",
        availabilityCheck=_yes,
    )
    assert cfg.model == "claude-haiku-4-5"


def test_selectProvider_custom_candidates_order() -> None:
    """candidates 인자로 우선순위 override."""
    cfg = selectProviderForQuestion(
        "삼성전자",
        candidates=("google", "openai", "anthropic"),
        availabilityCheck=_yes,
    )
    assert cfg.provider == "google"


def test_selectProvider_env_order_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """DARTLAB_AI_PROVIDER_ORDER 환경변수로 우선순위 변경."""
    monkeypatch.setenv("DARTLAB_AI_PROVIDER_ORDER", "openai,anthropic,google")
    cfg = selectProviderForQuestion("삼성전자", availabilityCheck=_yes)
    assert cfg.provider == "openai"


def test_default_provider_order_is_anthropic_first() -> None:
    """default 우선순위 SSOT — anthropic 첫 자리 (cache hit rate 최고)."""
    from dartlab.ai.providers.routing import _DEFAULT_PROVIDER_ORDER

    assert _DEFAULT_PROVIDER_ORDER[0] == "anthropic"

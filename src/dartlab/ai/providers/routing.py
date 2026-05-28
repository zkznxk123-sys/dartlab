"""Provider 자동 선택 + tier routing — 마스터 플랜 v2 트랙 7 PR-M3.

routeModelByComplexity (PR-L3) 가 *모델명만* 결정했다면, 본 모듈은 *provider 도* 자동 선택.
운영자 명시 provider 가 없을 때 (a) 가용성 검사 (b) 우선순위 (c) tier 매핑 3 단계 거쳐
ProviderConfig 반환. createProvider 와 결합해 1-line factory:

    from dartlab.ai.providers.routing import selectProviderForQuestion
    cfg = selectProviderForQuestion("삼성전자 DCF")
    provider = createProvider(cfg)

회귀 가드: 본 모듈은 ``createProvider`` 자체는 호출하지 않는다 (의존 방향 = 단방향). 호출자가
반환된 ProviderConfig 를 createProvider 에 넘긴다. 단위 테스트는 가용성 mock 만 검사.
"""

from __future__ import annotations

import os
from typing import Any

from dartlab.ai.providers import ProviderConfig, getConfig, routeModelByComplexity

# tier routing 지원 provider 우선순위 — 가용한 첫 provider 선택.
# anthropic 우선 (캐시 hit rate 가장 높음 — PR-L3 결정). 다음 openai (자동 prompt cache),
# 마지막 google (context caching 별도 비용). oauth-codex 는 tier routing 미지원 (단일 모델
# 정책) — 우선순위 외 (호출자가 provider="oauth-codex" 명시 시 별도 처리).
_DEFAULT_PROVIDER_ORDER: tuple[str, ...] = ("anthropic", "openai", "google")


def _envProviderOrder() -> tuple[str, ...]:
    """``DARTLAB_AI_PROVIDER_ORDER`` 환경변수 (comma sep) → tuple. 없으면 default."""
    raw = (os.environ.get("DARTLAB_AI_PROVIDER_ORDER") or "").strip()
    if not raw:
        return _DEFAULT_PROVIDER_ORDER
    items = tuple(part.strip().lower() for part in raw.split(",") if part.strip())
    return items or _DEFAULT_PROVIDER_ORDER


def _providerAvailable(providerName: str, *, availabilityCheck: Any | None = None) -> bool:
    """provider 가 인증 / SDK 양쪽 갖췄는지 — createProvider 없이 cheap 검사.

    ``availabilityCheck`` 인자가 callable 이면 그걸 호출 (테스트 injection). 기본은 환경변수
    api_key 존재 여부 검사 (provider 별 표준 env key).
    """
    if availabilityCheck is not None:
        return bool(availabilityCheck(providerName))
    env_key = _envKeyForProvider(providerName)
    if env_key is None:
        return False
    return bool(os.environ.get(env_key))


def _envKeyForProvider(providerName: str) -> str | None:
    """provider → api key env var 이름. routing 가능 provider 한정."""
    return {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "google": "GOOGLE_API_KEY",
        "gemini": "GEMINI_API_KEY",
    }.get(providerName.lower())


def selectProviderForQuestion(
    question: str,
    *,
    preferProvider: str | None = None,
    configuredTier: str | None = None,
    candidates: tuple[str, ...] | None = None,
    availabilityCheck: Any | None = None,
) -> ProviderConfig:
    """질문 → ProviderConfig (provider + tier-routed model) 자동 결정.

    Sig:
        selectProviderForQuestion(question, *, preferProvider=None, configuredTier=None,
            candidates=None, availabilityCheck=None) -> ProviderConfig
    Args:
        question: 사용자 질문 본문 — tier 추론 입력.
        preferProvider: 운영자 명시 우선 provider. 가용하면 그걸 사용, 아니면 candidates 폴백.
        configuredTier: cheap/standard/deep 강제 (routeModelByComplexity 인자 그대로).
        candidates: 시도 순서. None 이면 ``DARTLAB_AI_PROVIDER_ORDER`` 환경변수 / 기본.
        availabilityCheck: 테스트 injection. None 이면 env var 검사.
    Returns:
        ``ProviderConfig(provider=..., model=...)``. 가용 provider 0 이면 ``provider=None``
        ``model=None`` 반환 — 호출자가 명시 fallback (UnavailableProvider).
    Example:
        >>> cfg = selectProviderForQuestion("DCF 평가")
        >>> cfg.provider  # 'anthropic'
        >>> cfg.model    # 'claude-opus-4-7' (deep tier 추론)
    """
    order: tuple[str, ...] = candidates or _envProviderOrder()
    if preferProvider:
        norm = preferProvider.strip().lower()
        if _providerAvailable(norm, availabilityCheck=availabilityCheck):
            model = routeModelByComplexity(question, norm, configuredTier=configuredTier)
            return getConfig(provider=norm, model=model)
        # preferProvider 미가용 → candidates 폴백
    for provider in order:
        if not _providerAvailable(provider, availabilityCheck=availabilityCheck):
            continue
        model = routeModelByComplexity(question, provider, configuredTier=configuredTier)
        if model is None:
            continue
        return getConfig(provider=provider, model=model)
    # 가용 0 → null ProviderConfig (UnavailableProvider 가 호출 시 RuntimeError)
    return ProviderConfig(provider=None, model=None)


__all__ = [
    "_DEFAULT_PROVIDER_ORDER",
    "selectProviderForQuestion",
]

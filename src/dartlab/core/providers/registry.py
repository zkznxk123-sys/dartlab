"""AI provider 카탈로그 — 메타데이터, 정규화, 카탈로그 빌드. core 강등 SSOT.

이전: src/dartlab/ai/settings/provider_catalog.py (0.10 까지 shim 유지)
사유: provider 카탈로그는 cross-cutting primitive (ai/cli/server/core 모두 소비).
외부 L2 의존 0, AI_ROLES 도 동시에 강등됨 (`core/providers/routing.py`).

추가: `getDefaultProvider()` — credentials 가 ai 의 profile 모듈을 import 하지
않도록 ~/.dartlab/ai_profile.json 의 defaultProvider 필드만 직접 읽는 thin
헬퍼.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from dartlab.core.providers.routing import AI_ROLES


@dataclass(frozen=True)
class ProviderSpec:
    """AI provider 메타데이터 — 인증 방식, 프로빙 정책, 지원 역할."""

    id: str
    label: str
    description: str
    auth_kind: str
    public: bool = True
    setup_kind: str = "runtime"
    env_key: str | None = None
    probe_policy: str = "on_demand"
    supported_roles: tuple[str, ...] = AI_ROLES
    signupUrl: str | None = None
    freeTierHint: str | None = None


_PROVIDERS: dict[str, ProviderSpec] = {
    "oauth-codex": ProviderSpec(
        id="oauth-codex",
        label="GPT (ChatGPT 구독 계정)",
        description="브라우저 OAuth 로그인, GUI 대화/분석 권장",
        auth_kind="oauth",
        setup_kind="oauth",
        probe_policy="selected_only",
    ),
    "gemini": ProviderSpec(
        id="gemini",
        label="Google Gemini",
        description="Gemini 2.5 Pro/Flash",
        auth_kind="api_key",
        setup_kind="api_key",
        env_key="GEMINI_API_KEY",
        probe_policy="credentialed",
        signupUrl="https://aistudio.google.com/apikey",
    ),
    "codex": ProviderSpec(
        id="codex",
        label="Codex CLI (코딩용)",
        description="Codex CLI 로그인 기반 에이전트. GUI 일반 대화/분석용으로는 비권장",
        auth_kind="cli",
        setup_kind="cli",
        probe_policy="selected_only",
        supported_roles=("coding",),
    ),
    "ollama": ProviderSpec(
        id="ollama",
        label="Ollama (로컬)",
        description="오프라인, 프라이빗",
        auth_kind="none",
        setup_kind="local",
        probe_policy="selected_only",
    ),
    "openai": ProviderSpec(
        id="openai",
        label="OpenAI API",
        description="최신 GPT/Reasoning 모델",
        auth_kind="api_key",
        setup_kind="api_key",
        env_key="OPENAI_API_KEY",
        probe_policy="credentialed",
        signupUrl="https://platform.openai.com/api-keys",
    ),
    "custom": ProviderSpec(
        id="custom",
        label="Custom OpenAI-Compatible",
        description="OpenAI 호환 API 엔드포인트",
        auth_kind="api_key",
        setup_kind="api_key",
        probe_policy="credentialed",
    ),
    "groq": ProviderSpec(
        id="groq",
        label="Groq",
        description="Groq Cloud — 초고속 추론, LLaMA 3.3 70B",
        auth_kind="api_key",
        setup_kind="api_key",
        env_key="GROQ_API_KEY",
        probe_policy="credentialed",
        signupUrl="https://console.groq.com/keys",
    ),
    "cerebras": ProviderSpec(
        id="cerebras",
        label="Cerebras",
        description="Cerebras Inference — LLaMA 3.3 70B",
        auth_kind="api_key",
        setup_kind="api_key",
        env_key="CEREBRAS_API_KEY",
        probe_policy="credentialed",
        signupUrl="https://cloud.cerebras.ai/",
    ),
    "mistral": ProviderSpec(
        id="mistral",
        label="Mistral AI",
        description="Mistral AI — 다양한 모델",
        auth_kind="api_key",
        setup_kind="api_key",
        env_key="MISTRAL_API_KEY",
        probe_policy="credentialed",
        signupUrl="https://console.mistral.ai/api-keys",
    ),
}


def normalizeProvider(provider: str | None) -> str | None:
    """provider 문자열 정규화. 알려진 provider면 그대로, 아니면 원본 반환."""
    if provider is None:
        return None
    normalized = provider.strip()
    return normalized if normalized in _PROVIDERS else provider


def getProviderSpec(provider: str) -> ProviderSpec | None:
    """provider id로 ProviderSpec 조회. 미등록이면 None."""
    normalized = normalizeProvider(provider)
    if normalized is None:
        return None
    return _PROVIDERS.get(normalized)


def publicProviderIds() -> tuple[str, ...]:
    """공개(public=True) provider id 튜플."""
    return tuple(spec.id for spec in _PROVIDERS.values() if spec.public)


def wiredProviderIds() -> frozenset[str]:
    """카탈로그 등록 provider id 전체 (public + hidden). LLM 판정 단일 출처.

    `kernel._isLLMProvider`, `workbench.loop._isLLMProvider`, 그 외 provider
    검증 코드는 본 함수만 사용. hardcoded set 중복 금지.
    """
    return frozenset(_PROVIDERS.keys())


def providerChoices(*, includeHidden: bool = False) -> list[str]:
    """선택 가능한 provider id 목록."""
    return [spec.id for spec in _PROVIDERS.values() if includeHidden or spec.public]


def cliProviderChoices() -> list[str]:
    """CLI에서 사용 가능한 provider id 목록."""
    return providerChoices()


def buildProviderCatalog(*, includeHidden: bool = False) -> list[dict[str, str | list[str]]]:
    """전체 provider 카탈로그를 JSON-safe list[dict]로 반환."""
    items: list[dict[str, str | list[str]]] = []
    for spec in _PROVIDERS.values():
        if not includeHidden and not spec.public:
            continue
        item: dict[str, str | list[str]] = {
            "id": spec.id,
            "label": spec.label,
            "description": spec.description,
            "authKind": spec.auth_kind,
            "setupKind": spec.setup_kind,
            "probePolicy": spec.probe_policy,
            "supportedRoles": list(spec.supported_roles),
        }
        if spec.env_key:
            item["envKey"] = spec.env_key
        if spec.signupUrl:
            item["signupUrl"] = spec.signupUrl
        if spec.freeTierHint:
            item["freeTierHint"] = spec.freeTierHint
        items.append(item)
    return items


def apiKeySecretName(provider: str) -> str:
    """provider의 API 키 SecretStore 키 이름."""
    normalized = normalizeProvider(provider) or provider
    return f"provider:{normalized}:api_key"


def oauthSecretName(provider: str) -> str:
    """provider의 OAuth 토큰 SecretStore 키 이름."""
    normalized = normalizeProvider(provider) or provider
    return f"provider:{normalized}:oauth"


def _profilePath() -> Path:
    """~/.dartlab/ai_profile.json 경로 (ai/settings/profile.AiProfileManager 와 동일)."""
    raw = os.environ.get("DARTLAB_HOME")
    home = Path(raw) if raw else (Path.home() / ".dartlab")
    return home / "ai_profile.json"


def getDefaultProvider() -> str | None:
    """ai_profile.json 의 defaultProvider 필드만 직접 읽는 thin 헬퍼.

    core/credentials 가 ai/settings/profile (전체 AiProfileManager) 를 import
    하지 않도록 분리. 파일 미존재·파싱 실패 시 None.
    """
    path = _profilePath()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    value = data.get("defaultProvider") or data.get("provider")
    if not isinstance(value, str):
        return None
    return normalizeProvider(value)

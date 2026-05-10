"""스마트 AI provider auto-detection.

우선순위: 프리미엄 → 무료 API → 로컬/CLI
각 provider별 가벼운 체크로 사용 가능한 첫 번째를 반환.
"""

from __future__ import annotations

# 감지 우선순위: 프리미엄(이미 인증) → 무료(env key) → 로컬/CLI
_DETECT_ORDER = (
    "oauth-codex",
    "openai",
    "gemini",
    "groq",
    "cerebras",
    "mistral",
    "ollama",
    "codex",
)
from dartlab.core.logger import getLogger

_log = getLogger(__name__)


def _quickCheck(providerId: str) -> bool:
    """provider 사용 가능 여부를 빠르게 체크."""
    try:
        from dartlab.ai.providers import createProvider
        from dartlab.ai.settings.types import LLMConfig

        config = LLMConfig(provider=providerId)
        prov = createProvider(config)
        return prov.checkAvailable()
    except (ImportError, RuntimeError, ConnectionError, OSError, ValueError):
        return False


def autoDetectProvider(*, verbose: bool = False) -> str | None:
    """사용 가능한 provider를 우선순위 순으로 탐색.

    Args:
        verbose: True면 감지 실패 시 안내 메시지 출력.

    Returns:
        사용 가능한 provider id. 모두 실패 시 None.
    """
    for providerId in _DETECT_ORDER:
        if _quickCheck(providerId):
            return providerId

    if verbose:
        from dartlab.ai.settings.aiSetup import no_provider_message

        _log.info(no_provider_message())

    return None

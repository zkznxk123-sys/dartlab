"""AI provider 설정 안내 — provider 가용성 체크 + status 테이블.

_SETUP_GUIDES, _PROVIDER_ALIAS, resolveAlias, providerGuide, noProviderMessage
는 0.10 부터 core/providers/setupGuide 로 이전됨. 본 모듈은 가용성 체크
(`_check_provider_available`) 와 status 테이블 (`providers_status`) 만 잔존
(둘 다 ai.providers / ai.settings.types 의존).
"""

from __future__ import annotations

from dartlab.core.providers import _PROVIDERS
from dartlab.core.providers.setupGuide import (
    _PROVIDER_ALIAS,
    _SETUP_GUIDES,
    DISPLAY_ORDER,
    noProviderMessage,
    providerGuide,
    resolveAlias,
)

# snake alias — 0.10 까지 backward-compat shim. 0.11 제거.
resolve_alias = resolveAlias
provider_guide = providerGuide
no_provider_message = noProviderMessage
_DISPLAY_ORDER = DISPLAY_ORDER


def _check_provider_available(provider_id: str) -> bool:
    """provider 사용 가능 여부를 빠르게 체크 (네트워크 최소화)."""
    try:
        from dartlab.ai.providers import create_provider
        from dartlab.ai.settings.types import LLMConfig

        config = LLMConfig(provider=provider_id)
        prov = create_provider(config)
        return prov.check_available()
    except (ImportError, RuntimeError, ConnectionError, OSError, ValueError):
        return False


def providers_status() -> str:
    """전체 AI provider 현황을 테이블 문자열로 반환."""
    lines = ["", "  AI Provider 현황", ""]

    for pid in DISPLAY_ORDER:
        spec = _PROVIDERS.get(pid)
        guide = _SETUP_GUIDES.get(pid)
        if spec is None or guide is None:
            continue

        available = _check_provider_available(pid)
        marker = "●" if available else "○"
        status = "✓ 사용 가능" if available else "✗ 설정 필요"
        name = guide["name"]
        display_width = sum(2 if ord(c) > 127 else 1 for c in name)
        padded_name = name + " " * max(0, 20 - display_width)
        lines.append(f"  {marker} {pid:<15s} {padded_name} {status}")

    lines.append("")
    lines.append('  설정: dartlab.setup("provider이름")')
    lines.append('  예시: dartlab.setup("chatgpt")')
    lines.append("")
    return "\n".join(lines)


__all__ = [
    "DISPLAY_ORDER",
    "_DISPLAY_ORDER",
    "_PROVIDER_ALIAS",
    "_SETUP_GUIDES",
    "_check_provider_available",
    "noProviderMessage",
    "no_provider_message",
    "providerGuide",
    "providers_status",
    "provider_guide",
    "resolveAlias",
    "resolve_alias",
]

"""AI provider 설정 안내 — provider 가용성 체크 + status 테이블.

_SETUP_GUIDES, _PROVIDER_ALIAS, resolveAlias, providerGuide, noProviderMessage
는 0.10 부터 core/providers/setupGuide 로 이전됨. 본 모듈은 가용성 체크
(`_checkProviderAvailable`) 와 status 테이블 (`providersStatus`) 만 잔존
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
resolveAlias = resolveAlias
providerGuide = providerGuide
noProviderMessage = noProviderMessage
_DISPLAY_ORDER = DISPLAY_ORDER


def _checkProviderAvailable(providerId: str) -> bool:
    """provider 사용 가능 여부를 빠르게 체크 (네트워크 최소화).

    best-effort probe — 계약상 bool 만 반환하고 절대 예외를 전파하지 않는다.
    개별 provider client 초기화가 어떤 이유로든 실패하면 (미설치·키 오류·SDK
    시그니처 변경 등) "사용 불가" 로 간주한다. 한 provider 의 오류가 status
    테이블 전체(providersStatus)나 dartlab.setup() 진입을 깨뜨리면 안 된다.
    """
    try:
        from dartlab.ai.providers import createProvider
        from dartlab.ai.settings.types import LLMConfig

        config = LLMConfig(provider=providerId)
        prov = createProvider(config)
        return prov.checkAvailable()
    except Exception:  # noqa: BLE001 — 가용성 probe 는 어떤 오류도 "사용 불가" 로 흡수
        return False


def providersStatus() -> str:
    """전체 AI provider 현황을 테이블 문자열로 반환."""
    lines = ["", "  AI Provider 현황", ""]

    for pid in DISPLAY_ORDER:
        spec = _PROVIDERS.get(pid)
        guide = _SETUP_GUIDES.get(pid)
        if spec is None or guide is None:
            continue

        available = _checkProviderAvailable(pid)
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
    "_checkProviderAvailable",
    "noProviderMessage",
    "noProviderMessage",
    "providerGuide",
    "providersStatus",
    "providerGuide",
    "resolveAlias",
    "resolveAlias",
]

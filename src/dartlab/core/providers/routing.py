"""AI 역할(role) 정의 및 정규화 — core 강등 SSOT.

이전: src/dartlab/ai/settings/routing.py (0.10 까지 shim 유지)
사유: AI_ROLES 는 cross-cutting primitive (provider 카탈로그·credentials·CLI
모두 참조). 외부 L2 의존 0, ai 도메인 비의존.
"""

from __future__ import annotations

AI_ROLES: tuple[str, ...] = ("analysis", "summary", "coding", "ui_control")
DEFAULT_ROLE = "analysis"


def normalizeRole(role: str | None) -> str | None:
    """role 문자열을 정규화. 알려진 role이면 반환, 아니면 None."""
    if role is None:
        return None
    normalized = role.strip().lower()
    return normalized if normalized in AI_ROLES else None

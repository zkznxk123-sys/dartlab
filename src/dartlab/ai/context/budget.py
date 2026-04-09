"""토큰 예산 + 우선순위 트리밍.

provider별 컨텍스트 한도를 기준으로 ContextPart 리스트를 정리.
CRITICAL은 절대 제거하지 않고, OPTIONAL부터 자른다.
"""

from __future__ import annotations

from dartlab.ai.context.bundle import ContextPart, PartPriority

# provider별 안전 컨텍스트 예산 (system + user 합계 기준 권장치)
# 보수적으로 설정 — 응답 토큰 여유 확보.
_PROVIDER_BUDGETS: dict[str, int] = {
    "gemini": 30000,
    "openai": 12000,
    "groq": 6000,
    "cerebras": 6000,
    "mistral": 8000,
    "ollama": 4000,
    "claude": 30000,
    "claude_code": 30000,
    "codex": 12000,
    "oauth_codex": 12000,
}

_DEFAULT_BUDGET = 8000


def budgetFor(provider: str | None) -> int:
    """provider 이름 → 권장 컨텍스트 예산 토큰."""
    if not provider:
        return _DEFAULT_BUDGET
    return _PROVIDER_BUDGETS.get(provider.lower(), _DEFAULT_BUDGET)


def trim(
    parts: list[ContextPart],
    *,
    budgetTokens: int,
) -> tuple[list[ContextPart], list[str]]:
    """우선순위 기반 트리밍.

    Returns:
        (kept, droppedKeys)
        - kept: 예산 안에 들어간 parts (priority 내림차순)
        - droppedKeys: 잘려나간 part key 리스트
    """
    # priority 내림차순 정렬 (높은 우선순위 먼저)
    sorted_parts = sorted(parts, key=lambda p: p.priority, reverse=True)

    kept: list[ContextPart] = []
    dropped: list[str] = []
    used = 0

    for part in sorted_parts:
        # CRITICAL은 예산 초과해도 무조건 포함 (안전장치)
        if part.priority == PartPriority.CRITICAL:
            kept.append(part)
            used += part.estimatedTokens
            continue

        if used + part.estimatedTokens <= budgetTokens:
            kept.append(part)
            used += part.estimatedTokens
        else:
            dropped.append(part.key)

    return kept, dropped

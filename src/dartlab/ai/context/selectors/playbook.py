"""Playbook selector — ACE evolving playbook을 ContextPart로 주입.

intent 별 retrieval된 bullet들을 한 ContextPart로 합쳐 HIGH 우선순위로 주입.
Phase 1.5에서 14축 calc selectors와 함께 동작.
"""

from __future__ import annotations

from typing import Any

from dartlab.ai.context.bundle import ContextPart, PartPriority
from dartlab.ai.context.encoder import estimateTokens
from dartlab.ai.context.playbook import retrieveBullets


def selectPlaybookBullets(
    intent: str,
    company: Any | None,
    *,
    limit: int = 6,
) -> list[ContextPart]:
    """intent + sector 매칭 playbook bullets → ContextPart.

    Returns:
        [ContextPart] — bullets가 있으면 1개, 없으면 빈 리스트.
    """
    if not intent or intent == "act_all":
        # ACT_ALL fallback은 노이즈 우려 — playbook 주입 생략
        return []

    sector = ""
    if company is not None:
        sector = (
            getattr(company, "sector", None)
            or getattr(company, "sectorName", None)
            or ""
        )

    bullets = retrieveBullets(intent, sector=str(sector), limit=limit)
    if not bullets:
        return []

    # ACE 페이퍼 형식: 번호 매긴 짧은 bullet 리스트
    body = "\n".join(f"- {b}" for b in bullets)
    text = (
        '<playbook source="ace-curator">\n'
        f"## 학습된 분석 지침 ({intent})\n"
        "이전 분석에서 검증된 관점입니다. 현재 데이터에 적용하되 맹신하지 마세요.\n\n"
        f"{body}\n"
        "</playbook>"
    )

    return [
        ContextPart(
            key="ace.playbook",
            text=text,
            priority=PartPriority.HIGH,
            estimatedTokens=estimateTokens(text),
            source=f"knowledgedb:playbook[{intent}]",
        )
    ]

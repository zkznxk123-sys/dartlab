"""ai/context — Context Engineering 레이어 (Phase 1).

Anthropic / DSPy / Manus 계열의 context engineering 패턴을 dartlab에 적용.
prompt engineering 단계의 고정 텍스트 블록 주입을 동적 컨텍스트 빌더로 대체.

핵심 사상:
- intent 분류 → selector 동적 호출 → ContextBundle 조립
- 토큰 예산 우선순위 트리밍
- TOON 인코딩으로 같은 데이터를 30~60% 적은 토큰으로 주입
- selfai 폐기 학습 적용: 자동 최적화 X. 모든 선택은 명시적 결정론.

진입점:
    from dartlab.ai.context import ContextBuilder
    bundle = ContextBuilder(question=q, company=c, provider="gemini").build()

레이아웃:
    intent.py    — 질문 → Intent (6막 + compare + concept)
    selectors/   — Intent별 컨텍스트 선택자
    budget.py    — provider별 토큰 한도 + 우선순위 트리밍
    encoder.py   — TOON 인코딩
    builder.py   — ContextBuilder 메인 진입점
    bundle.py    — ContextBundle dataclass
"""

from __future__ import annotations

from dartlab.ai.context.builder import ContextBuilder
from dartlab.ai.context.bundle import ContextBundle, ContextPart, PartPriority
from dartlab.ai.context.intent import Intent, classifyIntent

__all__ = [
    "ContextBuilder",
    "ContextBundle",
    "ContextPart",
    "Intent",
    "PartPriority",
    "classifyIntent",
]

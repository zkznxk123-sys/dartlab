"""ContextBundle — ContextBuilder 출력 자료구조.

builder는 selector들이 만든 ContextPart 리스트를 priority + budget에 따라
트리밍하여 최종 ContextBundle을 만든다. 소비자(_analyze_inner)는
bundle.toUserParts() 로 기존 userParts 리스트와 호환되는 형태를 얻는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class PartPriority(IntEnum):
    """우선순위 — 낮을수록 먼저 트리밍된다.

    예산 부족 시 LOW부터 제거하고 CRITICAL은 절대 제거하지 않는다.
    """

    CRITICAL = 100  # 분석 대상 종목/회사명 — 절대 트리밍 금지
    HIGH = 80  # 14축 calc 결과 (intent 매칭)
    MEDIUM = 60  # 인사이트, 그래프 traversal
    LOW = 40  # 외부 검색, 메모리 힌트
    OPTIONAL = 20  # few-shot 예시


@dataclass(frozen=True)
class ContextPart:
    """단일 컨텍스트 블록.

    selector가 생성하고 builder가 budget에 따라 취사선택한다.
    """

    key: str  # selector 식별자 (예: "act2.marginTrend")
    text: str  # 사람이 읽는 텍스트 (TOON 또는 마크다운)
    priority: PartPriority
    estimatedTokens: int  # rough — len(text) // 3 정도면 충분
    source: str = ""  # 출처 (예: "calc:profitability", "knowledgedb:insight")

    def __post_init__(self) -> None:
        if not self.text:
            raise ValueError(f"ContextPart.text empty: key={self.key}")


@dataclass
class ContextBundle:
    """ContextBuilder 최종 출력.

    소비자는 toUserParts() 로 기존 코드 (_analyze_inner) 와 호환되는 리스트를 얻는다.
    parts 는 priority 내림차순 정렬되어 있다.
    """

    parts: list[ContextPart] = field(default_factory=list)
    intent: str = ""
    totalTokens: int = 0
    droppedKeys: list[str] = field(default_factory=list)  # budget으로 잘린 part keys

    def toUserParts(self) -> list[str]:
        """기존 _analyze_inner userParts 호환 — text 리스트만."""
        return [p.text for p in self.parts]

    def keys(self) -> list[str]:
        return [p.key for p in self.parts]

    def __len__(self) -> int:
        return len(self.parts)

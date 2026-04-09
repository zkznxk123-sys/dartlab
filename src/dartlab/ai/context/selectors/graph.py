"""Graph selector — 인과 질문 시 그래프 traversal 결과 ContextPart 주입.

intent가 어느 막이든, "왜" 키워드가 포함된 질문이면 추가로 호출됨.
"""

from __future__ import annotations

from typing import Any

from dartlab.ai.context.bundle import ContextPart, PartPriority
from dartlab.ai.context.encoder import estimateTokens

_WHY_KEYWORDS = ("왜", "원인", "이유", "때문", "어째서", "근거", "뭐 때문")


def _isWhyQuestion(question: str) -> bool:
    return any(kw in question for kw in _WHY_KEYWORDS)


def _extractTarget(question: str) -> str:
    """질문에서 분석 대상 지표를 추출 → 그래프 노드 label로 매핑."""
    # 키워드 → 그래프 노드 label (builder.py에서 사용한 이름과 일치해야 함)
    _KEYWORD_TO_LABEL = [
        ("영업이익률", "영업이익률"),
        ("마진", "영업이익률"),  # "마진" → 영업이익률 노드
        ("순이익률", "순이익률"),
        ("매출총이익률", "매출총이익률"),
        ("ROIC", "ROIC"),
        ("ROE", "ROIC"),  # ROE → ROIC 노드 (가장 가까운)
        ("부채비율", "부채비율"),
        ("부채", "부채비율"),
        ("FCF", "FCF"),
        ("현금흐름", "영업CF"),
        ("OCF", "영업CF"),
        ("Z-Score", "Z-Score"),
        ("Z스코어", "Z-Score"),
        ("매출", "매출액"),
        ("CAPEX", "CAPEX"),
        ("WACC", "WACC"),
    ]
    q = question.lower()
    for kw, label in _KEYWORD_TO_LABEL:
        if kw.lower() in q:
            return label
    return ""


def selectGraphCauses(
    question: str,
    company: Any | None,
) -> list[ContextPart]:
    """인과 질문 → graph causes traversal → ContextPart."""
    if not _isWhyQuestion(question) or company is None:
        return []

    target = _extractTarget(question)
    if not target:
        return []

    try:
        from dartlab.analysis.graph import buildGraph
        from dartlab.analysis.graph.traverse import causesNarrative, timelineNarrative
    except ImportError:
        return []

    try:
        g = buildGraph(company)
    except (KeyError, TypeError, ValueError, FileNotFoundError, OSError, RuntimeError):
        return []

    if len(g) == 0:
        return []

    # causes + timeline 서사 합산
    parts_text: list[str] = []
    cn = causesNarrative(g, target)
    if "찾을 수 없습니다" not in cn:
        parts_text.append(cn)
    tn = timelineNarrative(g, target)
    if "데이터 없음" not in tn:
        parts_text.append(tn)

    if not parts_text:
        return []

    text = '<context source="graph:causes">\n' + "\n\n".join(parts_text) + f"\n\n그래프: {g.summary()}\n</context>"

    return [
        ContextPart(
            key="graph.causes",
            text=text,
            priority=PartPriority.HIGH,
            estimatedTokens=estimateTokens(text),
            source=f"graph:causes[{target}]",
        )
    ]

"""기존 pre-grounding 헬퍼 래핑 selector.

Phase 1의 첫 마일스톤: 동작 변경 없이 ai/context/ 구조로 옮긴다.
기존 ai/runtime/core.py 의 5개 헬퍼를 호출하여 ContextPart로 변환만 한다.
회귀가 없는지 확인한 다음, analysis calc selector로 대체한다.

대응 관계:
    _searchCompanyCodes      → selectCompanySearch       (CRITICAL — 종목코드 식별)
    _preGroundDisclosure     → selectDisclosureBrief     (HIGH — 공시 프로필)
    _preGroundSearch         → selectExternalSearch      (LOW — 외부 검색)
    _gatherInsightHints      → selectInsightHints        (MEDIUM — KnowledgeDB)
    (memory hints 인라인)    → selectMemoryHints         (LOW — 세션 간 메모리)
"""

from __future__ import annotations

from typing import Any

from dartlab.ai.context.bundle import ContextPart, PartPriority
from dartlab.ai.context.encoder import estimateTokens


def selectCompanySearch(question: str, company: Any | None) -> list[ContextPart]:
    """company=None일 때 종목명 사전 검색."""
    if company is not None:
        return []
    try:
        from dartlab.ai.runtime.core import _searchCompanyCodes
    except ImportError:
        return []
    text = _searchCompanyCodes(question)
    if not text:
        return []
    return [
        ContextPart(
            key="legacy.companySearch",
            text=text,
            priority=PartPriority.CRITICAL,
            estimatedTokens=estimateTokens(text),
            source="dartlab.searchName",
        )
    ]


def selectDisclosureBrief(stockCode: str | None) -> list[ContextPart]:
    """공시 프로필 (companyProfile.parquet)."""
    if not stockCode:
        return []
    try:
        from dartlab.ai.runtime.core import _preGroundDisclosure
    except ImportError:
        return []
    text = _preGroundDisclosure(stockCode=stockCode)
    if not text:
        return []
    return [
        ContextPart(
            key="legacy.disclosureBrief",
            text=text,
            priority=PartPriority.HIGH,
            estimatedTokens=estimateTokens(text),
            source="core.search.derived.loadProfile",
        )
    ]


def selectExternalSearch(
    question: str,
    stockCode: str | None,
    corpName: str | None,
) -> list[ContextPart]:
    """외부 뉴스/웹 검색 — 키워드 트리거 시에만."""
    try:
        from dartlab.ai.runtime.core import _needsExternalSearch, _preGroundSearch
    except ImportError:
        return []
    if not _needsExternalSearch(question):
        return []
    text = _preGroundSearch(question, stockCode=stockCode, corpName=corpName)
    if not text:
        return []
    return [
        ContextPart(
            key="legacy.externalSearch",
            text=text,
            priority=PartPriority.LOW,
            estimatedTokens=estimateTokens(text),
            source="gather.search",
        )
    ]


def selectInsightHints(stockCode: str | None, company: Any | None) -> list[ContextPart]:
    """KnowledgeDB insight + sector_insights fallback."""
    if not stockCode:
        return []
    try:
        from dartlab.ai.runtime.core import _gatherInsightHints
    except ImportError:
        return []
    text = _gatherInsightHints(stockCode, company)
    if not text:
        return []
    return [
        ContextPart(
            key="legacy.insightHints",
            text=text,
            priority=PartPriority.MEDIUM,
            estimatedTokens=estimateTokens(text),
            source="ai.persistence.KnowledgeDB",
        )
    ]


def selectMemoryHints(stockCode: str | None, limit: int = 3) -> list[ContextPart]:
    """세션 간 메모리 — 이전 질문 이력 (수치 제외)."""
    if not stockCode:
        return []
    try:
        import datetime

        from dartlab.ai.memory.store import getMemory
    except ImportError:
        return []
    try:
        records = getMemory().recallForStock(stockCode, limit=limit)
    except (OSError, RuntimeError):
        return []
    if not records:
        return []
    lines = []
    for r in records:
        try:
            dt = datetime.datetime.fromtimestamp(r.timestamp).strftime("%Y-%m-%d")
            lines.append(f"- {dt}: {r.question} ({r.questionType})")
        except (AttributeError, OSError, ValueError):
            continue
    if not lines:
        return []
    text = "## 이전 질문 이력\n" + "\n".join(lines)
    return [
        ContextPart(
            key="legacy.memoryHints",
            text=text,
            priority=PartPriority.LOW,
            estimatedTokens=estimateTokens(text),
            source="ai.memory.store",
        )
    ]

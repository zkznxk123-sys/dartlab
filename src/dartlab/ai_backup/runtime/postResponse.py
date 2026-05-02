"""post-response 학습 — AI 응답 후 자동 실행되는 저장/큐레이션 훅.

src/dartlab/ai/README.md §2 의 "post-response 학습 (자율성 침해 아님)" 블록.
runtime/core.py::_runAskInner 에서 응답 종료 시 호출.

3 훅:
- persistence.store.saveAnalysis — executions 테이블 (general 포함)
- playbook.saveInsightFromResponse — insights (regex 추출, stockCode 있을 때만)
- playbook.curate           — ACE bullet delta merge (arxiv.org/abs/2510.04618)
"""

from __future__ import annotations

import sqlite3
from typing import Any


def runPostResponse(
    *,
    question: str,
    stockCode: str | None,
    company: Any | None,
    response_text: str,
) -> None:
    """AI 응답 종료 시 호출. 실패해도 silently 통과 (메인 흐름 영향 없음)."""
    if not response_text:
        return

    # 1. memory.saveAnalysis — general 질문도 executions 추적
    try:
        from dartlab.ai.persistence.store import getMemory
        from dartlab.ai.persistence.summarizer import extractGrade, summarizeResponse

        _mem = getMemory()
        _mem.saveAnalysis(
            stockCode=stockCode or "",
            question=question[:200],
            questionType="analysis",
            resultSummary=summarizeResponse(response_text),
            grade=extractGrade(response_text),
        )
    except (ImportError, OSError, sqlite3.Error):
        pass

    # 2. 자기성장 insights — stockCode 있고 응답 충분할 때만
    if stockCode and len(response_text) > 500:
        try:
            from dartlab.ai.context.playbook import saveInsightFromResponse

            saveInsightFromResponse(stockCode, response_text, company)
        except (ImportError, OSError, sqlite3.Error, AttributeError, ValueError):
            pass

    # 3. ACE Curator — bullet delta merge
    try:
        from dartlab.ai.context.intent import classifyIntent
        from dartlab.ai.context.playbook import curate
        from dartlab.ai.persistence.summarizer import extractGrade

        _intent = classifyIntent(question, hasCompany=company is not None).intent.value
        _sector = ""
        if company is not None:
            _sector = getattr(company, "sector", None) or getattr(company, "sectorName", None) or ""
        curate(
            intent=_intent,
            response_text=response_text,
            grade=extractGrade(response_text),
            sector=str(_sector),
            source="reflection",
        )
    except (ImportError, OSError, sqlite3.Error, AttributeError, ValueError):
        pass

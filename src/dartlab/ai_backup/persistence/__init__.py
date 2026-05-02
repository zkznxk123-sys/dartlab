"""ai 엔진 영속성 — KnowledgeDB + 분석 메모리 + 요약.

dartlab AI 의 단일 영속 패키지. Phase 17 C1 에서 memory/ 폴더 통합.

모듈:
    knowledge_db.py — 단일 DB (executions/insights/playbook/meta 테이블)
    store.py        — AnalysisMemory (executions 테이블 경계 레이어)
    summarizer.py   — 규칙 기반 응답 요약/등급 추출

대표 진입점:
    >>> from dartlab.ai.persistence import KnowledgeDB
    >>> db = KnowledgeDB.get()
    >>> db.save_execution(...)
"""

from __future__ import annotations

from dartlab.ai.persistence.knowledge_db import KnowledgeDB
from dartlab.ai.persistence.store import AnalysisMemory, getMemory

__all__ = ["KnowledgeDB", "AnalysisMemory", "getMemory"]


def _get_db():
    """KnowledgeDB 싱글턴 안전 접근. 실패 시 None."""
    try:
        return KnowledgeDB.get()
    except (OSError, RuntimeError):
        return None

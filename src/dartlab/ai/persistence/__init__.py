"""ai 엔진 영속성 — KnowledgeDB.

dartlab AI 의 단일 영속 저장소. selfai 폐기 후 영속성 책임만 분리해서 보존.

테이블:
    - executions: 모든 AI 실행 기록 (질문/결과/등급/모드)
    - insights:   기업별 심층 분석 서사 (자기성장 루프)
    - skills:     성공한 코드 패턴 (legacy, 폐기 예정)
    - error_patterns: 에러 패턴 (legacy, 폐기 예정)
    - meta:       DB 버전 / 마이그레이션 상태

대표 진입점:
    >>> from dartlab.ai.persistence import KnowledgeDB
    >>> db = KnowledgeDB.get()
    >>> db.save_execution(...)
    >>> db.get_insight("005930")
"""

from __future__ import annotations

from dartlab.ai.persistence.knowledge_db import KnowledgeDB

__all__ = ["KnowledgeDB"]

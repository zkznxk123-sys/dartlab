"""세션 transcript cross-session 검색 (SQLite FTS5).

`~/.claude/projects/.../*.jsonl` 트랜스크립트 (1 GB+ dark data) 를 인덱싱하여
과거 분석·결정·도구 호출 흔적을 BM25 검색.

`decisions.py` 의 BM25 가 *의사결정 memo* 만 다루는 것과 결을 맞춰 — 본 모듈은
*전체 대화 transcript* 검색. 두 모듈 모두 ~/.dartlab/ai_memory/ 아래 저장.

저장: ~/.dartlab/ai_memory/sessionIndex.db (SQLite + FTS5).
env redirect: DARTLAB_SESSION_INDEX_PATH (테스트/외부 도구).
"""

from __future__ import annotations

from .indexer import indexAll, indexFile, sessionIndexPath
from .search import SearchHit, searchSessions

__all__ = [
    "SearchHit",
    "indexAll",
    "indexFile",
    "searchSessions",
    "sessionIndexPath",
]

"""sessionIndex FTS5 검색 — 쿼리 → 상위 N hits.

`decisions.recall` 의 BM25 와 결을 맞춰 — SearchHit 는 session_id/timestamp/role/snippet
을 노출한다. raw text 는 길 수 있으므로 FTS5 의 snippet() 함수로 ±5 토큰 발췌.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .indexer import _connect, _ensureSchema, sessionIndexPath


@dataclass
class SearchHit:
    """단일 검색 결과 — session 메타 + 발췌."""

    session_id: str
    timestamp: str | None
    role: str
    block_type: str
    snippet: str
    tool_name: str | None
    score: float


def _escapeQuery(query: str) -> str:
    """FTS5 MATCH 쿼리 안전 변환 — 사용자 입력은 phrase 매칭으로.

    FTS5 의 syntax 문자 (`"`, `*`, `(`, `)`, `:`, `-`, etc) 가 들어가면 syntax error.
    공백 분리된 토큰을 모두 phrase 로 감싸 AND 매칭. 빈 토큰·특수문자만은 skip.
    """
    tokens: list[str] = []
    for raw in query.split():
        clean = raw.strip().replace('"', "")
        if not clean:
            continue
        if not any(ch.isalnum() or ord(ch) >= 0x80 for ch in clean):
            continue
        tokens.append(f'"{clean}"')
    return " ".join(tokens)


def searchSessions(
    query: str,
    *,
    limit: int = 20,
    role: str | None = None,
    dbPath: Path | None = None,
) -> list[SearchHit]:
    """FTS5 MATCH 검색 — BM25 ranking.

    Args:
        query: 자유형 쿼리. 공백 분리 토큰 모두 AND 매칭.
        limit: 반환 hit 수.
        role: "user" / "assistant" 필터. None 이면 둘 다.
        dbPath: 인덱스 db 경로.

    Returns:
        SearchHit 리스트. BM25 score 오름차순 (낮을수록 더 관련).
    """
    db = dbPath or sessionIndexPath()
    if not db.exists():
        return []

    match_expr = _escapeQuery(query)
    if not match_expr:
        return []

    conn = _connect(db)
    _ensureSchema(conn)
    try:
        sql = (
            "SELECT session_id, timestamp, role, block_type, tool_name, "
            "snippet(entries_fts, 0, '<mark>', '</mark>', '...', 12) AS snippet, "
            "bm25(entries_fts) AS score "
            "FROM entries_fts "
            "WHERE entries_fts MATCH ? "
        )
        params: list[object] = [match_expr]
        if role in ("user", "assistant"):
            sql += "AND role = ? "
            params.append(role)
        sql += "ORDER BY score LIMIT ?"
        params.append(int(limit))

        try:
            rows = conn.execute(sql, params).fetchall()
        except sqlite3.OperationalError:
            return []

        return [
            SearchHit(
                session_id=row["session_id"],
                timestamp=row["timestamp"],
                role=row["role"],
                block_type=row["block_type"],
                snippet=row["snippet"] or "",
                tool_name=row["tool_name"],
                score=float(row["score"] or 0.0),
            )
            for row in rows
        ]
    finally:
        conn.close()

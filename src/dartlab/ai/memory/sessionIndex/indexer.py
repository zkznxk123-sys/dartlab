"""세션 transcript jsonl → SQLite FTS5 인덱서.

Claude Code 가 `~/.claude/projects/{project-slug}/*.jsonl` 에 저장하는 세션 로그를
스트리밍 파싱 → user/assistant 메시지의 text/thinking 블록만 추출 → FTS5 인덱싱.

비-텍스트 블록 (tool_use payload · image · attachment 메타) 은 제외 — 검색 가치가
text/thinking 본문 대비 낮고 인덱스 크기·노이즈만 키운다. tool_use 는 *이름만* 별도
컬럼에 저장하여 "이 도구를 어떤 맥락에서 썼나" 검색은 가능.
"""

from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_DEFAULT_INDEX_PATH = Path.home() / ".dartlab" / "ai_memory" / "sessionIndex.db"
_CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"


def sessionIndexPath() -> Path:
    """DARTLAB_SESSION_INDEX_PATH env > 기본 경로.

    Returns:
        SQLite db 파일 경로. 부모 디렉토리는 호출자 책임 (init/_connect 가 mkdir).
    """
    env = os.environ.get("DARTLAB_SESSION_INDEX_PATH")
    if env:
        return Path(env)
    return _DEFAULT_INDEX_PATH


def _connect(dbPath: Path) -> sqlite3.Connection:
    dbPath.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(dbPath)
    conn.row_factory = sqlite3.Row
    return conn


def _ensureSchema(conn: sqlite3.Connection) -> None:
    """스키마 idempotent — 이미 있으면 no-op."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            file_path TEXT NOT NULL,
            file_mtime REAL NOT NULL,
            first_ts TEXT,
            last_ts TEXT,
            entry_count INTEGER DEFAULT 0,
            indexed_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS entries (
            entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            timestamp TEXT,
            role TEXT NOT NULL,
            block_type TEXT NOT NULL,
            text TEXT NOT NULL,
            tool_name TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_entries_session
            ON entries(session_id);

        CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
            text,
            role UNINDEXED,
            session_id UNINDEXED,
            timestamp UNINDEXED,
            block_type UNINDEXED,
            tool_name UNINDEXED,
            content='entries',
            content_rowid='entry_id',
            tokenize='unicode61 remove_diacritics 2'
        );

        CREATE TRIGGER IF NOT EXISTS entries_ai AFTER INSERT ON entries BEGIN
            INSERT INTO entries_fts(rowid, text, role, session_id, timestamp, block_type, tool_name)
            VALUES (new.entry_id, new.text, new.role, new.session_id, new.timestamp, new.block_type, new.tool_name);
        END;

        CREATE TRIGGER IF NOT EXISTS entries_ad AFTER DELETE ON entries BEGIN
            INSERT INTO entries_fts(entries_fts, rowid, text) VALUES('delete', old.entry_id, old.text);
        END;
        """
    )
    conn.commit()


@dataclass
class _Block:
    role: str
    block_type: str
    text: str
    tool_name: str | None = None


def _extractBlocks(entry: dict[str, Any]) -> Iterator[_Block]:
    """jsonl 한 줄 → 인덱싱 가능한 블록 stream.

    type=user/assistant 만. message.content 가 list 이고 각 dict 의 type 별:
    - text: text 필드 그대로
    - thinking (assistant): thinking 필드
    - tool_use (assistant): name 만 (payload 는 노이즈)
    - tool_result (user): content 가 list 면 text 만 합치고, str 이면 그대로
    """
    role = entry.get("type")
    if role not in ("user", "assistant"):
        return
    msg = entry.get("message")
    if not isinstance(msg, dict):
        return
    content = msg.get("content")
    if isinstance(content, str):
        yield _Block(role=role, block_type="text", text=content)
        return
    if not isinstance(content, list):
        return
    for block in content:
        if not isinstance(block, dict):
            continue
        btype = block.get("type")
        if btype == "text":
            text = block.get("text") or ""
            if isinstance(text, str) and text.strip():
                yield _Block(role=role, block_type="text", text=text)
        elif btype == "thinking" and role == "assistant":
            text = block.get("thinking") or ""
            if isinstance(text, str) and text.strip():
                yield _Block(role=role, block_type="thinking", text=text)
        elif btype == "tool_use" and role == "assistant":
            name = block.get("name") or ""
            if isinstance(name, str) and name:
                yield _Block(role=role, block_type="tool_use", text=name, tool_name=name)
        elif btype == "tool_result":
            inner = block.get("content")
            if isinstance(inner, str) and inner.strip():
                yield _Block(role=role, block_type="tool_result", text=inner)
            elif isinstance(inner, list):
                parts: list[str] = []
                for sub in inner:
                    if isinstance(sub, dict) and sub.get("type") == "text":
                        t = sub.get("text") or ""
                        if isinstance(t, str):
                            parts.append(t)
                joined = "\n".join(p for p in parts if p.strip())
                if joined:
                    yield _Block(role=role, block_type="tool_result", text=joined)


def _streamEntries(filePath: Path) -> Iterator[dict[str, Any]]:
    """jsonl 스트리밍 — 한 줄 = 한 entry. 깨진 줄은 skip."""
    with filePath.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def indexFile(filePath: Path, *, dbPath: Path | None = None, forceReindex: bool = False) -> int:
    """단일 jsonl 인덱싱.

    Args:
        filePath: jsonl 파일 경로.
        dbPath: SQLite db 경로. None 이면 sessionIndexPath().
        forceReindex: True 이면 기존 session_id 항목 삭제 후 재인덱싱.
            False 이면 mtime 비교하여 변경 없으면 skip.

    Returns:
        인덱싱된 entry 수. skip 시 0.
    """
    db = dbPath or sessionIndexPath()
    conn = _connect(db)
    _ensureSchema(conn)

    try:
        session_id = filePath.stem  # claude code 는 filename = sessionId
        mtime = filePath.stat().st_mtime

        if not forceReindex:
            row = conn.execute(
                "SELECT file_mtime FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if row and row["file_mtime"] >= mtime:
                return 0

        conn.execute("DELETE FROM entries WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))

        first_ts: str | None = None
        last_ts: str | None = None
        count = 0

        for entry in _streamEntries(filePath):
            ts = entry.get("timestamp")
            if isinstance(ts, str) and ts:
                if first_ts is None:
                    first_ts = ts
                last_ts = ts
            for block in _extractBlocks(entry):
                conn.execute(
                    "INSERT INTO entries(session_id, timestamp, role, block_type, text, tool_name) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        session_id,
                        ts if isinstance(ts, str) else None,
                        block.role,
                        block.block_type,
                        block.text,
                        block.tool_name,
                    ),
                )
                count += 1

        from datetime import datetime, timezone

        conn.execute(
            "INSERT INTO sessions(session_id, file_path, file_mtime, first_ts, last_ts, entry_count, indexed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (session_id, str(filePath), mtime, first_ts, last_ts, count, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        return count
    finally:
        conn.close()


def indexAll(
    projectsDir: Path | None = None,
    *,
    dbPath: Path | None = None,
    forceReindex: bool = False,
) -> dict[str, int]:
    """`~/.claude/projects/**/*.jsonl` 전체 sweep 인덱싱.

    Args:
        projectsDir: 기본 ~/.claude/projects. 테스트는 별도 경로 주입.
        dbPath: SQLite db 경로 (env 또는 기본).
        forceReindex: 모든 파일 강제 재인덱싱.

    Returns:
        {"files_total": ..., "files_indexed": ..., "entries_indexed": ...}
    """
    root = projectsDir or _CLAUDE_PROJECTS_DIR
    files_total = 0
    files_indexed = 0
    entries_indexed = 0

    if not root.exists():
        return {"files_total": 0, "files_indexed": 0, "entries_indexed": 0}

    for jsonl in root.rglob("*.jsonl"):
        files_total += 1
        added = indexFile(jsonl, dbPath=dbPath, forceReindex=forceReindex)
        if added > 0:
            files_indexed += 1
            entries_indexed += added

    return {
        "files_total": files_total,
        "files_indexed": files_indexed,
        "entries_indexed": entries_indexed,
    }

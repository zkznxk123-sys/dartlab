"""sessionIndex 인덱서 + 검색 + ai tool wrapper 회귀 가드.

`~/.claude/projects/.../*.jsonl` 포맷 변형:
- type=user / assistant + message.content (list of blocks)
- 각 block: type=text / thinking / tool_use / tool_result
- queue-operation 류 메타는 skip 대상
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _writeJsonl(path: Path, entries: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in entries) + "\n", encoding="utf-8")


@pytest.fixture
def tmp_session_index(tmp_path, monkeypatch):
    db = tmp_path / "sessionIndex.db"
    monkeypatch.setenv("DARTLAB_SESSION_INDEX_PATH", str(db))
    return db


@pytest.fixture
def fake_transcripts(tmp_path):
    """가짜 ~/.claude/projects/<slug>/{sessionId}.jsonl 한 쌍."""
    proj = tmp_path / "claude_projects" / "dartlab-fake"
    proj.mkdir(parents=True)

    s1 = proj / "session-aaa.jsonl"
    _writeJsonl(
        s1,
        [
            {"type": "queue-operation", "operation": "enqueue", "timestamp": "2026-05-01T00:00:00Z"},
            {
                "type": "user",
                "timestamp": "2026-05-01T00:00:01Z",
                "message": {
                    "role": "user",
                    "content": [{"type": "text", "text": "삼성전자 매핑 cycle 분석 좀"}],
                },
            },
            {
                "type": "assistant",
                "timestamp": "2026-05-01T00:00:05Z",
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "thinking", "thinking": "user wants 삼성전자 mapping cycle review"},
                        {"type": "text", "text": "매퍼 cycle 17 라운드 결과 정리한다"},
                        {"type": "tool_use", "name": "EngineCall", "input": {}},
                    ],
                },
            },
        ],
    )

    s2 = proj / "session-bbb.jsonl"
    _writeJsonl(
        s2,
        [
            {
                "type": "user",
                "timestamp": "2026-05-10T00:00:00Z",
                "message": {
                    "role": "user",
                    "content": [{"type": "text", "text": "Tesla 자율주행 마진 추정"}],
                },
            },
            {
                "type": "assistant",
                "timestamp": "2026-05-10T00:00:03Z",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Tesla FSD 마진 분리는 segment 미공개라 추정"}],
                },
            },
        ],
    )
    return proj


@pytest.mark.unit
def test_index_file_inserts_text_and_thinking_blocks(tmp_session_index, fake_transcripts):
    from dartlab.ai.memory.sessionIndex import indexFile

    files = sorted(fake_transcripts.glob("*.jsonl"))
    assert files, "fixture 누락"

    count = indexFile(files[0])
    assert count >= 3, f"text + thinking + tool_use 3+ entries, got {count}"


@pytest.mark.unit
def test_index_all_sweeps_directory(tmp_session_index, fake_transcripts):
    from dartlab.ai.memory.sessionIndex import indexAll

    stats = indexAll(projectsDir=fake_transcripts)
    assert stats["files_total"] == 2
    assert stats["files_indexed"] == 2
    assert stats["entries_indexed"] >= 4


@pytest.mark.unit
def test_search_finds_query_with_bm25_ranking(tmp_session_index, fake_transcripts):
    from dartlab.ai.memory.sessionIndex import indexAll, searchSessions

    indexAll(projectsDir=fake_transcripts)
    hits = searchSessions("삼성전자 매핑", limit=10)
    assert hits, "삼성전자 매핑 매칭 hit 0"
    assert any(h.session_id == "session-aaa" for h in hits)


@pytest.mark.unit
def test_search_role_filter(tmp_session_index, fake_transcripts):
    from dartlab.ai.memory.sessionIndex import indexAll, searchSessions

    indexAll(projectsDir=fake_transcripts)
    user_hits = searchSessions("삼성전자", limit=10, role="user")
    assistant_hits = searchSessions("매퍼", limit=10, role="assistant")
    assert all(h.role == "user" for h in user_hits)
    assert all(h.role == "assistant" for h in assistant_hits)


@pytest.mark.unit
def test_reindex_skipped_when_mtime_unchanged(tmp_session_index, fake_transcripts):
    from dartlab.ai.memory.sessionIndex import indexFile

    files = sorted(fake_transcripts.glob("*.jsonl"))
    first = indexFile(files[0])
    again = indexFile(files[0])
    assert first > 0
    assert again == 0, "mtime 변경 없는데 재인덱싱"


@pytest.mark.unit
def test_corrupt_jsonl_lines_skipped(tmp_session_index, tmp_path):
    from dartlab.ai.memory.sessionIndex import indexFile

    bad = tmp_path / "broken.jsonl"
    bad.write_text(
        "\n".join(
            [
                "{this is not json",
                json.dumps({"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "ok"}]}}),
                "",
            ]
        ),
        encoding="utf-8",
    )
    count = indexFile(bad)
    assert count == 1, "깨진 줄 1 + 빈 줄 1 skip, valid 1 만 인덱싱"


@pytest.mark.unit
def test_search_empty_query_returns_no_hits(tmp_session_index):
    from dartlab.ai.memory.sessionIndex import searchSessions

    assert searchSessions("", limit=5) == []
    assert searchSessions("   ", limit=5) == []


@pytest.mark.unit
def test_search_fts_special_chars_safely_handled(tmp_session_index, fake_transcripts):
    from dartlab.ai.memory.sessionIndex import indexAll, searchSessions

    indexAll(projectsDir=fake_transcripts)
    # FTS5 special chars (* " : - ()) 가 들어와도 syntax error 아닌 결과 반환
    hits = searchSessions('"삼성전자" (매핑*)', limit=5)
    assert isinstance(hits, list)


@pytest.mark.unit
def test_tool_search_past_sessions_returns_refs(tmp_session_index, fake_transcripts, monkeypatch):
    from dartlab.ai.memory.sessionIndex import indexAll
    from dartlab.ai.tools.searchPastSessions import searchPastSessions

    indexAll(projectsDir=fake_transcripts)
    result = searchPastSessions("Tesla 자율주행", limit=5)
    assert result.ok is True
    assert result.refs, "Tesla 자율주행 hits 0"
    assert all(r.kind == "sessionRef" for r in result.refs)
    assert result.data["hits"]


@pytest.mark.unit
def test_tool_search_empty_query_returns_error(tmp_session_index):
    from dartlab.ai.tools.searchPastSessions import searchPastSessions

    result = searchPastSessions("")
    assert result.ok is False
    assert result.error == "empty_query"


@pytest.mark.unit
def test_tool_registered_in_canonical():
    from dartlab.ai.tools.registry import CANONICAL_TOOL_NAMES, executeTool

    assert "SearchPastSessions" in CANONICAL_TOOL_NAMES
    out = executeTool("SearchPastSessions", {"query": "X"})
    assert "ok" in out

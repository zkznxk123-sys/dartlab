"""feedbackSignals 회귀 가드 — 부정/긍정 발화 추출 + system prompt 주입."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


def _seedSessionIndex(dbPath: Path, entries: list[dict]) -> None:
    dbPath.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(dbPath)
    conn.executescript(
        """
        CREATE TABLE entries (
            entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            timestamp TEXT,
            role TEXT NOT NULL,
            block_type TEXT NOT NULL,
            text TEXT NOT NULL,
            tool_name TEXT
        );
        """
    )
    for e in entries:
        conn.execute(
            "INSERT INTO entries(session_id, timestamp, role, block_type, text) VALUES (?, ?, ?, ?, ?)",
            (
                e.get("session_id", "s1"),
                e.get("timestamp", "2026-05-20T00:00:00Z"),
                e["role"],
                e.get("block_type", "text"),
                e["text"],
            ),
        )
    conn.commit()
    conn.close()


@pytest.fixture
def signals_db(tmp_path, monkeypatch):
    db = tmp_path / "sessionIndex.db"
    cache = tmp_path / "feedbackSignals.cache.json"
    _seedSessionIndex(
        db,
        [
            {"role": "user", "text": "삼성전자 분석 좀"},  # 무 시그널
            {"role": "user", "text": "무슨말하노 지금"},  # 부정
            {"role": "user", "text": "이해가 안된다"},  # 부정
            {"role": "user", "text": "좋다"},  # 긍정 (단어 그대로)
            {"role": "user", "text": "맞다 그게 정확"},  # 긍정
            {"role": "user", "text": "이게 무슨 클론?"},  # 부정
            {"role": "user", "text": "오케이 진행해"},  # 긍정
            {"role": "user", "text": "안녕"},  # _TRIVIAL — 제외
            {"role": "user", "text": "ㅋㅋㅋ"},  # _TRIVIAL — 제외
            {
                "role": "user",
                "text": "회사 분기 흐름 어때요 제가 보기엔 이번 분기는 좀 좋은 것 같아서 분석 좀 해주시면 좋겠는데요",
            },  # 너무 김 + 긍정 키워드 — _MAX_SIGNAL_LEN 초과로 제외
            {"role": "assistant", "text": "분석 결과..."},  # role=assistant 제외
        ],
    )
    monkeypatch.setenv("DARTLAB_SESSION_INDEX_PATH", str(db))
    monkeypatch.setenv("DARTLAB_FEEDBACK_SIGNALS_CACHE_PATH", str(cache))
    return {"db": db, "cache": cache}


@pytest.mark.unit
def test_extract_negatives(signals_db):
    from dartlab.ai.memory.dialectic import extractFeedbackSignals

    signals = extractFeedbackSignals(forceRefresh=True)
    assert "무슨말하노 지금" in signals.negatives
    assert "이해가 안된다" in signals.negatives
    assert "이게 무슨 클론?" in signals.negatives


@pytest.mark.unit
def test_extract_positives(signals_db):
    from dartlab.ai.memory.dialectic import extractFeedbackSignals

    signals = extractFeedbackSignals(forceRefresh=True)
    assert "좋다" in signals.positives
    assert "오케이 진행해" in signals.positives


@pytest.mark.unit
def test_trivial_utterances_excluded(signals_db):
    from dartlab.ai.memory.dialectic import extractFeedbackSignals

    signals = extractFeedbackSignals(forceRefresh=True)
    assert "안녕" not in signals.negatives + signals.positives
    assert "ㅋㅋㅋ" not in signals.negatives + signals.positives


@pytest.mark.unit
def test_long_utterances_excluded(signals_db):
    from dartlab.ai.memory.dialectic import extractFeedbackSignals

    signals = extractFeedbackSignals(forceRefresh=True)
    long_one = "회사 분기 흐름 어때요 제가 보기엔 이번 분기는 좀 좋은 것 같아서 분석 좀 해주시면 좋겠는데요"
    assert long_one not in signals.positives, "40+ chars 발화는 시그널 모호 — 제외"


@pytest.mark.unit
def test_assistant_text_excluded(signals_db):
    from dartlab.ai.memory.dialectic import extractFeedbackSignals

    signals = extractFeedbackSignals(forceRefresh=True)
    # assistant role 의 분석 결과 텍스트가 user 시그널에 섞이지 않아야
    assert "분석 결과..." not in signals.negatives + signals.positives


@pytest.mark.unit
def test_cache_hit_skips_resampling(signals_db, monkeypatch):
    from dartlab.ai.memory.dialectic import extractFeedbackSignals
    from dartlab.ai.memory.dialectic import feedbackSignals as mod

    extractFeedbackSignals(forceRefresh=True)
    called = {"count": 0}
    orig = mod._streamRecentUserTexts

    def _spy(*args, **kwargs):
        called["count"] += 1
        return orig(*args, **kwargs)

    monkeypatch.setattr(mod, "_streamRecentUserTexts", _spy)
    extractFeedbackSignals()  # 캐시 hit
    assert called["count"] == 0, "캐시 hit 시 재추출 안 함"


@pytest.mark.unit
def test_build_feedback_signals_block(signals_db):
    from dartlab.ai.memory.dialectic import buildFeedbackSignalsBlock

    block = buildFeedbackSignalsBlock(forceRefresh=True)
    assert "사용자 피드백 시그널" in block
    assert "부정 발화" in block
    assert "긍정 발화" in block
    assert "무슨말하노 지금" in block
    assert "좋다" in block


@pytest.mark.unit
def test_build_block_empty_when_no_signals(tmp_path, monkeypatch):
    from dartlab.ai.memory.dialectic import buildFeedbackSignalsBlock

    monkeypatch.setenv("DARTLAB_SESSION_INDEX_PATH", str(tmp_path / "missing.db"))
    monkeypatch.setenv("DARTLAB_FEEDBACK_SIGNALS_CACHE_PATH", str(tmp_path / "cache.json"))
    assert buildFeedbackSignalsBlock(forceRefresh=True) == ""


@pytest.mark.unit
def test_agent_inject_pipeline_includes_feedback_signals(signals_db, monkeypatch):
    """agent._injectPastContextIfAvailable 가 피드백 시그널 블록까지 부착하는지."""
    from dartlab.ai.agent import _injectPastContextIfAvailable

    # userProfile 도 같이 호출되므로 격리
    monkeypatch.setenv("DARTLAB_USER_PROFILE_CACHE_PATH", str(signals_db["db"].parent / "userProfile.cache.json"))
    out = _injectPastContextIfAvailable("BASE", {}, history=[{"role": "user", "content": "X"}])
    assert "사용자 피드백 시그널" in out
    assert "무슨말하노 지금" in out

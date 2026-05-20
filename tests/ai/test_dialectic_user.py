"""dialectic user model 회귀 가드 — userProfile + sessionIntent + 통합 블록."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pytest


def _seedSessionIndex(dbPath: Path, entries: list[dict]) -> None:
    """가짜 sessionIndex.db 생성 — 본 테스트용 최소 스키마."""
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
                e.get("timestamp", "2026-05-01T00:00:00Z"),
                e["role"],
                e.get("block_type", "text"),
                e["text"],
            ),
        )
    conn.commit()
    conn.close()


@pytest.fixture
def seeded_db(tmp_path, monkeypatch):
    db = tmp_path / "sessionIndex.db"
    cache = tmp_path / "userProfile.cache.json"
    entries = [
        {"role": "user", "text": "삼성전자 005930 매출 분석 좀"},
        {"role": "user", "text": "005930 영업이익 추이"},
        {"role": "user", "text": "반도체 신용도 dCR 어때"},
        {"role": "user", "text": "회귀 가드 lint 추가"},
        {"role": "assistant", "text": "분석 결과 ..."},  # role=assistant 는 무시되어야
    ]
    # TSLA 35 회 등장 — _MIN_TICKER_COUNT=30 임계 통과해야 top_tickers 진입
    for _ in range(35):
        entries.append({"role": "user", "text": "Tesla TSLA 자율주행 마진 검토"})
    _seedSessionIndex(db, entries)
    monkeypatch.setenv("DARTLAB_SESSION_INDEX_PATH", str(db))
    monkeypatch.setenv("DARTLAB_USER_PROFILE_CACHE_PATH", str(cache))
    return {"db": db, "cache": cache}


@pytest.mark.unit
def test_user_profile_counts_user_turns_only(seeded_db):
    from dartlab.ai.memory.dialectic import userInterestProfile

    profile = userInterestProfile(forceRefresh=True)
    # 4 일반 + 35 TSLA 반복 = 39 user turns. assistant 1 건은 제외.
    assert profile.total_user_turns == 39, "user role + block_type=text 만 카운트"


@pytest.mark.unit
def test_user_profile_extracts_kr_stock_codes(seeded_db):
    from dartlab.ai.memory.dialectic import userInterestProfile

    profile = userInterestProfile(forceRefresh=True)
    sc = dict(profile.top_stock_codes)
    assert sc.get("005930") == 2, "005930 두 번 등장"


@pytest.mark.unit
def test_user_profile_extracts_us_ticker_skips_false_positives(seeded_db):
    from dartlab.ai.memory.dialectic import userInterestProfile

    profile = userInterestProfile(forceRefresh=True)
    tickers = dict(profile.top_tickers)
    assert "TSLA" in tickers, "TSLA 매칭"
    # KR / US / AI 등은 _KR_FALSE_TICKER 로 차단되어야 (regex 매칭은 되지만 skip)
    assert "KR" not in tickers
    assert "AI" not in tickers


@pytest.mark.unit
def test_user_profile_theme_breakdown(seeded_db):
    from dartlab.ai.memory.dialectic import userInterestProfile

    profile = userInterestProfile(forceRefresh=True)
    themes = profile.theme_breakdown
    assert themes.get("재무분석", 0) >= 1, "매출/영업이익 키워드"
    assert themes.get("신용도", 0) >= 1, "dcr 키워드"
    assert themes.get("회귀가드", 0) >= 1, "회귀/lint 키워드"


@pytest.mark.unit
def test_user_profile_cache_hit(seeded_db):
    from dartlab.ai.memory.dialectic import userInterestProfile

    p1 = userInterestProfile(forceRefresh=True)
    assert seeded_db["cache"].exists()
    p2 = userInterestProfile()  # 캐시 hit
    assert p1.generated_at == p2.generated_at, "캐시 hit 시 generated_at 동일"


@pytest.mark.unit
def test_session_intent_extracts_from_history():
    from dartlab.ai.memory.dialectic import sessionIntent

    history = [
        {"role": "user", "content": "삼성전자 005930 분석 좀 해봐"},
        {"role": "assistant", "content": "분석 시작..."},
        {"role": "user", "content": "Tesla TSLA 마진 비교 검증"},
    ]
    intent = sessionIntent(history)
    assert intent.turn_count == 2
    assert "005930" in dict(intent.session_stock_codes)
    assert "TSLA" in dict(intent.session_tickers)
    assert intent.intent_hint == "verify", "마지막 발화 '검증' → verify"


@pytest.mark.unit
def test_session_intent_classifies_action_keyword():
    from dartlab.ai.memory.dialectic import sessionIntent

    history = [{"role": "user", "content": "이거 박아봐"}]
    assert sessionIntent(history).intent_hint == "action"


@pytest.mark.unit
def test_session_intent_empty_history():
    from dartlab.ai.memory.dialectic import sessionIntent

    intent = sessionIntent([])
    assert intent.turn_count == 0


@pytest.mark.unit
def test_build_user_context_block_combines_profile_and_intent(seeded_db):
    from dartlab.ai.memory.dialectic import buildUserContextBlock

    history = [{"role": "user", "content": "005930 검증 좀"}]
    block = buildUserContextBlock(history, forceRefresh=True)
    assert "사용자 컨텍스트" in block
    assert "누적" in block
    assert "이번 세션" in block
    assert "005930" in block  # 누적 + 세션 둘 다 등장


@pytest.mark.unit
def test_build_user_context_block_empty_when_no_data(tmp_path, monkeypatch):
    from dartlab.ai.memory.dialectic import buildUserContextBlock

    monkeypatch.setenv("DARTLAB_SESSION_INDEX_PATH", str(tmp_path / "missing.db"))
    monkeypatch.setenv("DARTLAB_USER_PROFILE_CACHE_PATH", str(tmp_path / "cache.json"))
    block = buildUserContextBlock(None, forceRefresh=True)
    assert block == ""


@pytest.mark.unit
def test_agent_inject_pipeline_includes_user_context(seeded_db, monkeypatch):
    """agent.py 의 _injectPastContextIfAvailable 가 user context 까지 부착하는지 통합 검증."""
    from dartlab.ai.agent import _injectPastContextIfAvailable

    # 합성 view memoryDir 가 dartlab 메모리로 자동 sweep — 환경변수 None 으로 자동 탐색 허용
    history = [{"role": "user", "content": "005930 분석"}]
    out = _injectPastContextIfAvailable("BASE_PROMPT", {}, history=history)
    assert "사용자 컨텍스트" in out, "user context 블록 부착 안 됨"
    assert "005930" in out

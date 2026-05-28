"""aiMetricsDigest.py 단위 테스트.

마스터 플랜 트랙 2 PR-O5 동행. trace dump 글로브 + 집계 + KPI verdict 결정론 검증.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.audit.aiMetricsDigest import (
    _aggregate,
    _kpiVerdict,
    _loadTraces,
    _parseDuration,
    _percentile,
    _renderText,
)

pytestmark = pytest.mark.unit


def test_parseDuration_units() -> None:
    """30d / 7d / 24h / 60m 모두 정확히 초 변환."""
    assert _parseDuration("30d") == 30 * 86400
    assert _parseDuration("7d") == 7 * 86400
    assert _parseDuration("24h") == 24 * 3600
    assert _parseDuration("60m") == 60 * 60
    assert _parseDuration("5") == 5 * 86400  # default unit = d


def test_parseDuration_invalid() -> None:
    with pytest.raises(ValueError):
        _parseDuration("invalid")


def test_percentile_basic() -> None:
    """percentile linear interpolation."""
    assert _percentile([], 50) is None
    assert _percentile([10.0], 95) == 10.0
    assert _percentile([1.0, 2.0, 3.0, 4.0, 5.0], 50) == 3.0
    assert _percentile([1.0, 2.0, 3.0, 4.0, 5.0], 95) == pytest.approx(4.8, abs=1e-3)


def test_loadTraces_missing_dir(tmp_path: Path) -> None:
    """디렉토리 없으면 빈 리스트."""
    missing = tmp_path / "nonexistent"
    assert _loadTraces(missing) == []


def test_loadTraces_invalid_json_skipped(tmp_path: Path) -> None:
    """잘못된 JSON 파일은 skip."""
    (tmp_path / "broken.json").write_text("not json", encoding="utf-8")
    (tmp_path / "good.json").write_text(json.dumps({"sessionId": "x", "events": []}), encoding="utf-8")
    traces = _loadTraces(tmp_path)
    assert len(traces) == 1
    assert traces[0]["sessionId"] == "x"


def test_aggregate_empty() -> None:
    """trace 0 → sessionCount 0."""
    stats = _aggregate([])
    assert stats["sessionCount"] == 0
    assert stats["turnsPerSession"]["p95"] is None


def test_aggregate_full_session_events() -> None:
    """단일 세션 events → turn / first_chunk_ms / tool_result 집계."""
    trace = {
        "sessionId": "abc",
        "question": "삼성전자 DCF",
        "provider": "scripted",
        "events": [
            {"kind": "first_chunk_ms", "data": {"ms": 1500.0, "iter": 0}},
            {"kind": "turn_timing", "data": {"iter": 0, "elapsedMs": 800.0, "toolCallCount": 1}},
            {"kind": "tool_result", "data": {"tool": "DCFValuation"}},
            {"kind": "turn_timing", "data": {"iter": 1, "elapsedMs": 1200.0, "toolCallCount": 0, "final": True}},
            {"kind": "done", "data": {}},
        ],
    }
    stats = _aggregate([trace])
    assert stats["sessionCount"] == 1
    assert stats["turnsPerSession"]["p95"] == 2.0
    assert stats["firstChunkMs"]["count"] == 1
    assert stats["firstChunkMs"]["p95"] == 1500.0
    assert stats["turnElapsedMs"]["count"] == 2
    # tool 빈도
    tools = dict(stats["toolTop20"])
    assert tools.get("DCFValuation") == 1


def test_aggregate_error_kinds() -> None:
    """error 이벤트 누적."""
    trace = {
        "events": [
            {"kind": "error", "data": {"error": "provider_error"}},
            {"kind": "error", "data": {"error": "dead_loop"}},
            {"kind": "error", "data": {"error": "provider_error"}},
        ],
    }
    stats = _aggregate([trace])
    assert stats["errors"]["provider_error"] == 2
    assert stats["errors"]["dead_loop"] == 1


def test_kpiVerdict_passes_when_targets_met() -> None:
    """목표값 만족 → passed=True."""
    stats = {
        "turnsPerSession": {"p95": 3.0},
        "firstChunkMs": {"p95": 1500.0},
    }
    verdict = _kpiVerdict(stats)
    names = {name: passed for name, _target, passed in verdict}
    assert names["turnsPerSession.p95"] is True
    assert names["firstChunkMs.p95"] is True


def test_kpiVerdict_fails_when_targets_breached() -> None:
    """목표 초과 → passed=False."""
    stats = {
        "turnsPerSession": {"p95": 8.0},
        "firstChunkMs": {"p95": 3000.0},
    }
    verdict = _kpiVerdict(stats)
    names = {name: passed for name, _target, passed in verdict}
    assert names["turnsPerSession.p95"] is False
    assert names["firstChunkMs.p95"] is False


def test_renderText_empty_session_count() -> None:
    """0 세션 → 활성 안내 문구."""
    stats = _aggregate([])
    text = _renderText(stats, since=None)
    assert "세션 수: 0" in text
    assert "DARTLAB_AI_TRACE_DUMP" in text


def test_renderText_with_session() -> None:
    """세션 있으면 KPI 라인 모두 노출."""
    trace = {
        "events": [
            {"kind": "first_chunk_ms", "data": {"ms": 1000.0}},
            {"kind": "turn_timing", "data": {"iter": 0, "elapsedMs": 500.0, "toolCallCount": 0, "final": True}},
        ],
    }
    stats = _aggregate([trace])
    text = _renderText(stats, since=86400 * 7)
    assert "세션 수: 1" in text
    assert "turns/session" in text
    assert "firstChunk ms" in text
    assert "KPI 목표 vs 실측" in text

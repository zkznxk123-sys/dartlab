"""workbenchUsageDigest 단위 테스트.

마스터 플랜 트랙 3 PR-W1 동행.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.audit.workbenchUsageDigest import (
    _loadTraces,
    _parseDuration,
    aggregate,
    renderText,
)

pytestmark = pytest.mark.unit


def test_parseDuration_units() -> None:
    assert _parseDuration("7d") == 7 * 86400
    assert _parseDuration("24h") == 24 * 3600
    assert _parseDuration("60m") == 60 * 60


def test_loadTraces_missing_dir(tmp_path: Path) -> None:
    assert _loadTraces(tmp_path / "nonexistent") == []


def test_aggregate_empty() -> None:
    stats = aggregate([])
    assert stats["sessionCount"] == 0
    assert stats["totalToolCalls"] == 0
    assert "측정 불가" in stats["verdict"]


def test_aggregate_low_workbench_pct_recommends_delete() -> None:
    """workbench < 1% → PR-W2-A (삭제) 권장."""
    # 100 tool_result 중 RunWorkbench 0 회 → 0%
    trace = {
        "events": [{"kind": "tool_result", "data": {"tool": "EngineCall"}} for _ in range(100)],
    }
    stats = aggregate([trace])
    assert stats["totalToolCalls"] == 100
    assert stats["runWorkbenchCalls"] == 0
    assert stats["workbenchPercent"] == 0.0
    assert "PR-W2-A" in stats["verdict"]
    assert "삭제" in stats["verdict"]


def test_aggregate_high_workbench_pct_recommends_keep() -> None:
    """workbench ≥ 1% → PR-W2-B (유지) 권장."""
    # 100 tool 중 RunWorkbench 2 회 → 2%
    events = [{"kind": "tool_result", "data": {"tool": "EngineCall"}} for _ in range(98)]
    events.extend([{"kind": "tool_result", "data": {"tool": "RunWorkbench"}} for _ in range(2)])
    trace = {"events": events}
    stats = aggregate([trace])
    assert stats["runWorkbenchCalls"] == 2
    assert stats["workbenchPercent"] == 2.0
    assert "PR-W2-B" in stats["verdict"]
    assert "유지" in stats["verdict"]


def test_aggregate_five_pass_event_kinds() -> None:
    """BRIEF/WORK/CRITIQUE 등 5 패스 event 누적."""
    trace = {
        "events": [
            {"kind": "BRIEF", "data": {}},
            {"kind": "WORK", "data": {}},
            {"kind": "WORK", "data": {}},
            {"kind": "CRITIQUE", "data": {}},
            {"kind": "tool_result", "data": {"tool": "EngineCall"}},
        ],
    }
    stats = aggregate([trace])
    assert stats["workbenchEvents"]["BRIEF"] == 1
    assert stats["workbenchEvents"]["WORK"] == 2
    assert stats["workbenchEvents"]["CRITIQUE"] == 1


def test_renderText_includes_verdict() -> None:
    """renderText 가 verdict 라인 포함."""
    stats = aggregate([])
    text = renderText(stats)
    assert "세션 수: 0" in text
    assert "결정:" in text


def test_loadTraces_valid_json(tmp_path: Path) -> None:
    """JSON 파일 정상 load."""
    p = tmp_path / "x.json"
    p.write_text(json.dumps({"sessionId": "x", "events": []}), encoding="utf-8")
    traces = _loadTraces(tmp_path)
    assert len(traces) == 1
    assert traces[0]["sessionId"] == "x"

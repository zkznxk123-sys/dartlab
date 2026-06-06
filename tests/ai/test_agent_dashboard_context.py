"""Phase 8/9 — dashboard snapshot 시스템 프롬프트 주입 unit tests.

agent.py 의 _injectPastContextIfAvailable + _formatDashboardSnapshotBlock 이
workspaceContext.dashboardSnapshot 을 trusted block 으로 변환해 시스템
프롬프트에 append 하는지 검증.
"""

from __future__ import annotations

import pytest

from dartlab.ai.agent import _formatDashboardSnapshotBlock, _injectPastContextIfAvailable

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _disableAmbientMemoryBlocks(monkeypatch: pytest.MonkeyPatch) -> None:
    """dashboardSnapshot 단위 테스트는 주변 memory prompt 주입을 격리한다."""
    monkeypatch.setattr("dartlab.ai.memory.synthesizer.buildToneBlock", lambda: "")
    monkeypatch.setattr("dartlab.ai.memory.dialectic.buildUserContextBlock", lambda history=None: "")
    monkeypatch.setattr("dartlab.ai.memory.dialectic.buildFeedbackSignalsBlock", lambda: "")


class TestFormatDashboardSnapshotBlock:
    """_formatDashboardSnapshotBlock 출력 검증."""

    def test_empty_snapshot_returns_empty(self):
        assert _formatDashboardSnapshotBlock({}) == ""

    def test_view_only(self):
        block = _formatDashboardSnapshotBlock({"dashboardView": "analysis"})
        assert "- 탭: `analysis`" in block

    def test_full_snapshot_has_all_fields(self):
        snap = {
            "dashboardView": "analysis",
            "stockCode": "035720",
            "axis": "수익성",
            "period": "TTM",
            "visibleKpis": [
                {"name": "ROE", "value": "8.4%"},
                {"name": "OPM", "value": "9.04%"},
            ],
        }
        block = _formatDashboardSnapshotBlock(snap)
        assert "- 탭: `analysis`" in block
        assert "- 회사: `035720`" in block
        assert "- 분석 axis: `수익성`" in block
        assert "- 기간: `TTM`" in block
        assert "ROE=8.4%" in block
        assert "OPM=9.04%" in block

    def test_string_kpis_fallback(self):
        block = _formatDashboardSnapshotBlock({"visibleKpis": ["raw KPI string"]})
        assert "raw KPI string" in block


class TestInjectPastContextIfAvailable:
    """_injectPastContextIfAvailable 의 dashboardSnapshot 분기 검증.

    기존 stockCode past_context 동작은 그대로 (회귀 0).
    """

    def test_no_kwargs_returns_original(self):
        result = _injectPastContextIfAvailable("BASE PROMPT", {})
        assert result == "BASE PROMPT"

    def test_dashboard_snapshot_appends_block(self):
        snap = {"dashboardView": "credit", "stockCode": "035720", "axis": "grade"}
        result = _injectPastContextIfAvailable("BASE PROMPT", {"dashboardSnapshot": snap})
        assert result.startswith("BASE PROMPT")
        assert "## 현재 대시보드 화면" in result
        assert "credit" in result
        assert "035720" in result
        assert "grade" in result

    def test_empty_snapshot_no_block(self):
        result = _injectPastContextIfAvailable("BASE PROMPT", {"dashboardSnapshot": {}})
        # 빈 snapshot 은 block 자체 없음 (환각 가드).
        assert result == "BASE PROMPT"

    def test_non_dict_snapshot_ignored(self):
        result = _injectPastContextIfAvailable("BASE PROMPT", {"dashboardSnapshot": "not a dict"})
        assert result == "BASE PROMPT"

    def test_dashboard_snapshot_marked_trusted(self):
        """'사용자 시야, 신뢰' marker 가 있어 untrusted 외부 본문과 구분된다."""
        snap = {"dashboardView": "analysis"}
        result = _injectPastContextIfAvailable("BASE PROMPT", {"dashboardSnapshot": snap})
        assert "신뢰" in result or "사용자 시야" in result

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_analysis_workspace_result_bundle_keeps_additive_fields():
    from dartlab.ai.runtime.workspace import AnalysisWorkspace

    workspace = AnalysisWorkspace(question="최근 주가지수")
    claims = workspace.recordFinalAnswer("최종 결론은 검증된 답변입니다.")
    bundle = workspace.resultBundle()

    assert claims
    assert "evidence" in bundle
    assert "claims" in bundle
    assert "visuals" in bundle
    assert "limits" in bundle


def test_workspace_visual_rejects_single_bar():
    from dartlab.ai.runtime.workspace_session import AgentSession
    from dartlab.ai.runtime.workspace_visual import hasDegenerateVisual

    session = AgentSession(question="최근 주가지수", workspaceRoot=Path.cwd(), dataRoot=Path.cwd())
    session.visuals.append(
        {
            "id": "viz_1",
            "spec": {
                "vizType": "chart",
                "chartType": "bar",
                "categories": ["summary"],
                "series": [{"name": "close", "data": [1]}],
            },
        }
    )

    assert hasDegenerateVisual(session) is True


def test_workspace_verify_blocks_finalize_without_visual_for_ranking(tmp_path):
    from dartlab.ai.runtime.workspace_session import AgentSession, Execution
    from dartlab.ai.runtime.workspace_verify import finalizeAnswer

    session = AgentSession(
        question="최근 주가지수를 보고 강세 지수를 찾아봐라", workspaceRoot=tmp_path, dataRoot=tmp_path
    )
    session.add_observation(source="data", metric="latestObservedDate", value="20260428", observedDate="20260428")
    session.executions.append(
        Execution(id="exec_1", code="print('ok')", stdout="ok", stderr="", returncode=0, durationMs=1)
    )

    result = finalizeAnswer(session, "데이터 기준일 20260428 기준입니다.", [], [], [])

    assert result["ok"] is False
    assert "missing_visual_explanation" in result["issues"]


def test_server_visual_dedupe_uses_spec_not_event_id():
    from dartlab.server.streaming import _dedupeVisuals

    spec = {
        "vizType": "chart",
        "chartType": "bar",
        "categories": ["A", "B"],
        "series": [{"name": "score", "data": [1, 2]}],
    }

    workspace_spec = {
        **spec,
        "purpose": "ranking",
        "options": {},
        "meta": {},
        "sourceArtifact": "same_table",
    }

    rows = _dedupeVisuals([{"id": "event_viz", "spec": spec}, {"id": "workspace_viz", "spec": workspace_spec}])

    assert len(rows) == 1

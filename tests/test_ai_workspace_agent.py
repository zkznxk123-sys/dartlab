from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_workspace_agent_inspects_data_and_records_latest_observation(tmp_path, monkeypatch):
    import polars as pl

    from dartlab import config
    from dartlab.ai.runtime.workspace_agent import AgentSession, _inspect_data

    monkeypatch.setattr(config, "dataDir", str(tmp_path))
    path = tmp_path / "indices.parquet"
    pl.DataFrame(
        {
            "BAS_DD": ["20260426", "20260428"],
            "IDX_NM": ["KOSPI", "KOSPI"],
            "CLSPRC_IDX": [3100.0, 3200.0],
        }
    ).write_parquet(path)

    session = AgentSession(question="최근 주가지수", workspaceRoot=tmp_path, dataRoot=tmp_path)
    result = _inspect_data(session, "indices.parquet")

    assert result["ok"] is True
    assert result["latest"] == {"column": "BAS_DD", "value": "20260428"}
    assert result["semanticProfile"]["dateColumns"] == ["BAS_DD"]
    assert "CLSPRC_IDX" in result["semanticProfile"]["metricCandidates"]
    assert session.observations[0].metric == "latestObservedDate"
    assert session.observations[0].observedDate == "20260428"


def test_workspace_status_exposes_intelligence_map(tmp_path):
    from dartlab.ai.runtime.workspace_agent import AgentSession, _workspace_status

    session = AgentSession(
        question="최근 주가지수를 보고 강세 지수를 찾아봐라", workspaceRoot=tmp_path, dataRoot=tmp_path
    )
    result = _workspace_status(session)

    assert result["agent"] == "DartLab Financial Workspace Agent"
    assert result["llmFacingTools"] == [
        "workspace_status",
        "read_text",
        "inspect_data",
        "run_python",
        "search_workspace",
        "create_artifact",
        "finalize_answer",
    ]
    assert result["intelligenceMap"]["name"] == "DartLab Financial Workspace Agent"
    assert result["intelligenceMap"]["pack"]["available"] is True
    assert "analysisGraph" in result["intelligenceMap"]
    meta = session.response_meta()["agent"]
    assert meta["packVersion"] == 1
    assert meta["packSourceHash"]


def test_search_workspace_prefers_intelligence_map(tmp_path):
    from dartlab.ai.runtime.workspace_agent import AgentSession, _search_workspace

    session = AgentSession(question="최근 주가가 많이 오른 종목 찾아줘", workspaceRoot=tmp_path, dataRoot=tmp_path)
    result = _search_workspace(session, "최근 주가 상승", kind="any", limit=5)

    assert result["ok"] is True
    assert any(
        str(row.get("kind", "")).startswith("intelligence") or row.get("kind") == "data" for row in result["results"]
    )
    assert session.response_meta()["agent"]["packHitCount"] >= 1


def test_workspace_agent_rejects_single_value_visual(tmp_path):
    from dartlab.ai.runtime.workspace_agent import AgentSession, _create_artifact

    session = AgentSession(question="최근 주가지수", workspaceRoot=tmp_path, dataRoot=tmp_path)
    result = _create_artifact(
        session,
        "visual",
        {
            "vizType": "chart",
            "chartType": "bar",
            "categories": ["summary"],
            "series": [{"name": "close", "data": [4000]}],
        },
        "bad_chart",
    )

    assert result["ok"] is False
    assert "degenerate" in result["error"]
    assert session.visuals == []


def test_workspace_agent_auto_visualizes_csv_for_ranking_question(tmp_path, monkeypatch):
    from dartlab import config
    from dartlab.ai.runtime.workspace_agent import AgentSession, _create_artifact

    monkeypatch.setattr(config, "dataDir", str(tmp_path))
    session = AgentSession(
        question="최근 주가지수를 보고 강세 지수를 찾아봐라", workspaceRoot=tmp_path, dataRoot=tmp_path
    )

    result = _create_artifact(
        session,
        "csv",
        [
            {"IDX_NM": "KOSPI", "close": 3000.0, "strength_score": 12.3},
            {"IDX_NM": "KOSDAQ", "close": 900.0, "strength_score": 4.5},
        ],
        "bullish_indices",
    )

    assert result["ok"] is True
    assert result["format"] == "csv"
    assert result["visual"]["spec"]["categories"] == ["KOSPI", "KOSDAQ"]
    assert result["visual"]["spec"]["series"][0]["name"] == "strength_score"
    assert result["visual"]["spec"]["series"][0]["data"] == [12.3, 4.5]
    assert session.visuals


def test_workspace_agent_finalize_catches_today_data_date_conflict(tmp_path):
    from dartlab.ai.runtime.workspace_agent import AgentSession, _finalize_answer

    session = AgentSession(
        question="최근 주가지수", workspaceRoot=tmp_path, dataRoot=tmp_path, currentDate="2026-04-30"
    )
    session.add_observation(source="data", metric="latestObservedDate", observedDate="20260428", value="20260428")

    result = _finalize_answer(
        session,
        "오늘은 2025-08-08입니다. 데이터 기준일은 20260428입니다.",
        evidence_refs=[],
        artifact_refs=[],
        limits=[],
    )

    assert result["ok"] is False
    assert "date_context_conflict" in result["issues"]


def test_workspace_agent_finalize_catches_recent_index_return_outlier(tmp_path):
    from dartlab.ai.runtime.workspace_agent import AgentSession, _finalize_answer

    session = AgentSession(
        question="최근 주가지수를 보고 강세 지수를 찾아봐라",
        workspaceRoot=tmp_path,
        dataRoot=tmp_path,
    )
    session.add_observation(source="data", metric="latestObservedDate", observedDate="20260428", value="20260428")
    session.executions.append(type("ExecutionStub", (), {"ok": True, "returncode": 0})())
    session.artifacts.append({"id": "artifact_1", "format": "csv"})
    session.visuals.append(
        {
            "id": "viz_1",
            "spec": {
                "vizType": "chart",
                "chartType": "bar",
                "categories": ["KOSPI", "KOSDAQ"],
                "series": [{"name": "return", "data": [10.0, 20.0]}],
            },
        }
    )

    result = _finalize_answer(session, "KOSPI 5일 수익률은 +3766.29%입니다.", [], [], [])

    assert result["ok"] is False
    assert "index_return_outlier" in result["issues"]


def test_workspace_agent_requires_csv_and_visual_for_ranking_questions(tmp_path):
    from dartlab.ai.runtime.workspace_agent import AgentSession, _finalize_answer

    session = AgentSession(
        question="최근 주가지수를 보고 강세 지수를 찾아봐라", workspaceRoot=tmp_path, dataRoot=tmp_path
    )
    session.add_observation(source="data", metric="latestObservedDate", observedDate="20260428", value="20260428")
    session.executions.append(
        type(
            "ExecutionStub",
            (),
            {"ok": True, "returncode": 0},
        )()
    )

    result = _finalize_answer(session, "데이터 기준일 20260428 기준 강세 지수입니다.", [], [], [])

    assert result["ok"] is False
    assert "missing_csv_artifact" in result["issues"]
    assert "missing_visual_explanation" in result["issues"]


def test_workspace_agent_loop_is_kernel_shim(monkeypatch):
    from dartlab.ai import kernel
    from dartlab.ai.contracts import TraceEvent
    from dartlab.ai.runtime.workspace_agent import buildWorkspaceAgentSystemPrompt, runWorkspaceAgent

    called = {}

    def fake_runask(question, **kwargs):
        called["question"] = question
        called["kwargs"] = kwargs
        yield TraceEvent("plan", {"entrySkillId": "start.dartlabSkillOs"})
        yield TraceEvent("answer", {"answer": "kernel 답변"})
        yield TraceEvent("chunk", {"text": "kernel 답변"})
        yield TraceEvent("done", {"responseMeta": {"kernel": "Ask Workbench Kernel"}})

    monkeypatch.setattr(kernel, "runAsk", fake_runask)

    messages = [
        {"role": "system", "content": buildWorkspaceAgentSystemPrompt(question="DartLab 뭐야?")},
        {"role": "user", "content": "질문: DartLab 뭐야?"},
    ]
    out = list(runWorkspaceAgent(object(), messages, question="DartLab 뭐야?", stockCode="005930"))

    assert called["question"] == "DartLab 뭐야?"
    assert called["kwargs"]["stockCode"] == "005930"
    assert "kernel 답변" in out
    assert any(getattr(ev, "kind", None) == "plan" for ev in out)


def test_runtime_core_runask_uses_kernel_path(monkeypatch):
    from dartlab.ai import kernel
    from dartlab.ai.contracts import TraceEvent
    from dartlab.ai.runtime.core import runAsk

    called = {}

    def fake_runask(question, **kwargs):
        called["question"] = question
        called["kwargs"] = kwargs
        yield TraceEvent("plan", {"entrySkillId": "start.dartlabSkillOs"})
        yield TraceEvent("answer", {"answer": "kernel 답변"})
        yield TraceEvent("chunk", {"text": "kernel 답변"})
        yield TraceEvent("done", {"responseMeta": {"kernel": "Ask Workbench Kernel"}})

    monkeypatch.setattr(kernel, "runAsk", fake_runask)

    events = list(runAsk("DartLab 뭐야?", provider="openai", emit_system_prompt=False))

    assert called["question"] == "DartLab 뭐야?"
    assert called["kwargs"]["provider"] == "openai"
    assert any(ev.kind == "plan" for ev in events)
    assert any(ev.kind == "chunk" and ev.data.get("text") == "kernel 답변" for ev in events)
    done = [ev for ev in events if ev.kind == "done"][-1]
    assert done.data["responseMeta"]["kernel"] == "Ask Workbench Kernel"

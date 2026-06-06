"""pipeline.orchestrator 단위 — runScript mock(실 스크립트 0), dispatch·격리 검증."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_list_and_describe_stages():
    """listStages/describeStages — 핵심 category 노출."""
    from dartlab.pipeline import describeStages, listStages

    stages = listStages()
    assert {"finance", "report", "panel", "krx", "macro", "news", "edgar"} <= set(stages)
    assert "docs" not in stages
    metas = describeStages()
    assert all({"category", "online", "uploadCategories", "label"} <= set(m) for m in metas)


def test_run_stage_finance_ok(monkeypatch):
    """runStage('finance') — syncRecent rc=0 → ok=1 (업로드 생략)."""
    import dartlab.pipeline.stages.dart as dart

    monkeypatch.setattr(dart, "runScript", lambda *a, **k: 0)
    res = dart.runDartRecent(category="finance", upload=False)
    assert res.category == "finance" and res.report.ok == 1 and res.report.err == 0


def test_run_stage_nonzero_rc_isolated(monkeypatch):
    """스크립트 rc!=0 → err 기록(크래시 X)."""
    import dartlab.pipeline.stages.dart as dart

    monkeypatch.setattr(dart, "runScript", lambda *a, **k: 7)
    res = dart.runDartRecent(category="report", upload=False)
    assert res.report.err == 1 and "rc=7" in res.report.failures[0]


def test_run_stage_unknown_raises():
    """미등록 stage → ValueError."""
    from dartlab.pipeline.orchestrator import runStage

    with pytest.raises(ValueError):
        runStage("nope")


def test_run_pipeline_isolation(monkeypatch):
    """runPipeline — 1 stage 예외가 나머지 중단 X(격리)."""
    import dartlab.pipeline.orchestrator as orch

    def fakeRunStage(category, *, mode, codes=None, upload, token=None):
        if category == "report":
            raise RuntimeError("boom")
        from dartlab.pipeline.types import StageResult

        r = StageResult(category=category)
        r.report.ok = 1
        return r

    monkeypatch.setattr(orch, "runStage", fakeRunStage)
    results = orch.runPipeline(["finance", "report", "panel"], upload=False)
    assert results["finance"].report.ok == 1
    assert results["panel"].report.ok == 1
    assert results["report"].report.fail == 1 and "boom" in results["report"].report.failures[0]


def test_panel_graceful_skip_missing_refdf(monkeypatch):
    """panel online — panelXbrlRef 부재 시 onlinePanel 실행 없이 graceful skip(un-gate 안전 핵심)."""
    import dartlab.pipeline.stages.dart as dart
    import dartlab.providers.dart.panel.build as panelBuild

    ran = {"n": 0}
    monkeypatch.setattr(dart, "runScript", lambda *a, **k: ran.__setitem__("n", ran["n"] + 1) or 0)
    monkeypatch.setattr(
        panelBuild, "panelXbrlRefPath", lambda: __import__("pathlib").Path("/no/such/panelXbrlRef.parquet")
    )
    res = dart.runDartPanel(category="panel", mode="online", upload=False)
    assert res.skipped is True
    assert ran["n"] == 0  # refDf 부재 → onlinePanel 미실행


def test_panel_runs_when_refdf_present(monkeypatch, tmp_path):
    """panel online — refDf 존재 시 onlinePanel 실행 + changed 0 이면 skip."""
    import dartlab.pipeline.stages.dart as dart
    import dartlab.providers.dart.panel.build as panelBuild

    ref = tmp_path / "panelXbrlRef.parquet"
    ref.write_bytes(b"x")
    monkeypatch.setattr(panelBuild, "panelXbrlRefPath", lambda: ref)
    monkeypatch.setattr(dart, "runScript", lambda *a, **k: 0)
    monkeypatch.setattr(dart, "readChanged", lambda c: [])
    res = dart.runDartPanel(category="panel", mode="online", upload=False)
    assert res.report.err == 0

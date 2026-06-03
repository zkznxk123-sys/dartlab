"""pipeline.orchestrator 단위 — runScript mock(실 스크립트 0), dispatch·격리 검증."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_list_and_describe_stages():
    """listStages/describeStages — 핵심 category 노출."""
    from dartlab.pipeline import describeStages, listStages

    stages = listStages()
    assert {"finance", "report", "docs", "panel", "sections", "krx", "macro", "news", "edgar"} <= set(stages)
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
    res = dart.runDartRecent(category="docs", upload=False)
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
    results = orch.runPipeline(["finance", "report", "docs"], upload=False)
    assert results["finance"].report.ok == 1
    assert results["docs"].report.ok == 1
    assert results["report"].report.fail == 1 and "boom" in results["report"].report.failures[0]


def test_panel_graceful_skip(monkeypatch):
    """panel — refDf 부재(changed 0)면 skipped=True."""
    import dartlab.pipeline.stages.dart as dart

    monkeypatch.setattr(dart, "runScript", lambda *a, **k: 0)
    monkeypatch.setattr(dart, "readChanged", lambda c: [])
    res = dart.runDartPanel(category="panel", mode="online", upload=False)
    assert res.skipped is True

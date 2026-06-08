"""pipeline reconcile (reconcileCategory + panel/edgarPanel stages) 단위 — 네트워크 0(stub)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_reconcile_category_set_difference(monkeypatch, tmp_path) -> None:
    """파일집합 차분 — HF에만 있으면 pull, 로컬에만 있으면 push (panel)."""
    from dartlab.pipeline import hfUpload as upmod
    from dartlab.pipeline import reconcile
    from dartlab.pipeline import seed as seedmod

    # 로컬 dart/panel/{A,B}.parquet
    pdir = tmp_path / "dart" / "panel"
    pdir.mkdir(parents=True)
    (pdir / "A.parquet").write_bytes(b"x")
    (pdir / "B.parquet").write_bytes(b"x")

    # HF 에는 {B,C}
    monkeypatch.setattr(
        seedmod, "listRemoteFiles", lambda category, token=None: {"dart/panel/B.parquet": 1, "dart/panel/C.parquet": 1}
    )

    pulled_arg = {}
    pushed_arg = {}

    def stubDownload(category, relPaths, *, dataDir=None, token=None):
        pulled_arg["rels"] = list(relPaths)
        return len(relPaths), 0

    def stubUpload(category, *, changedFiles=None, dataDir=None, token=None):
        pushed_arg["names"] = list(changedFiles or [])
        return len(changedFiles or [])

    monkeypatch.setattr(seedmod, "downloadCategoryFiles", stubDownload)
    monkeypatch.setattr(upmod, "uploadCategoryToHf", stubUpload)

    out = reconcile.reconcileCategory("panel", dataDir=str(tmp_path))
    assert out["pull"] == 1 and out["pulled"] == 1
    assert out["push"] == 1 and out["pushed"] == 1
    assert out["inSync"] is False
    assert pulled_arg["rels"] == ["dart/panel/C.parquet"]  # HF에만 → 로컬로
    assert pushed_arg["names"] == ["A.parquet"]  # 로컬에만 → HF로 (category dir 기준 파일명)


def test_reconcile_category_in_sync(monkeypatch, tmp_path) -> None:
    """로컬·HF 동일하면 처리 0 + inSync — 외부 호출 없음."""
    from dartlab.pipeline import hfUpload as upmod
    from dartlab.pipeline import reconcile
    from dartlab.pipeline import seed as seedmod

    pdir = tmp_path / "dart" / "panel"
    pdir.mkdir(parents=True)
    (pdir / "A.parquet").write_bytes(b"x")

    monkeypatch.setattr(seedmod, "listRemoteFiles", lambda category, token=None: {"dart/panel/A.parquet": 1})

    def boomDl(*a, **k):
        raise AssertionError("download 호출됨 — in-sync인데 pull")

    def boomUp(*a, **k):
        raise AssertionError("upload 호출됨 — in-sync인데 push")

    monkeypatch.setattr(seedmod, "downloadCategoryFiles", boomDl)
    monkeypatch.setattr(upmod, "uploadCategoryToHf", boomUp)

    out = reconcile.reconcileCategory("panel", dataDir=str(tmp_path))
    assert out["pull"] == 0 and out["push"] == 0 and out["inSync"] is True


def test_reconcile_category_push_disabled(monkeypatch, tmp_path) -> None:
    """push=False → 로컬전용 파일 push 안 함(pull만)."""
    from dartlab.pipeline import hfUpload as upmod
    from dartlab.pipeline import reconcile
    from dartlab.pipeline import seed as seedmod

    pdir = tmp_path / "dart" / "panel"
    pdir.mkdir(parents=True)
    (pdir / "A.parquet").write_bytes(b"x")  # 로컬에만

    monkeypatch.setattr(seedmod, "listRemoteFiles", lambda category, token=None: {"dart/panel/C.parquet": 1})
    monkeypatch.setattr(seedmod, "downloadCategoryFiles", lambda *a, **k: (1, 0))

    called = {"up": False}

    def stubUp(*a, **k):
        called["up"] = True
        return 0

    monkeypatch.setattr(upmod, "uploadCategoryToHf", stubUp)

    out = reconcile.reconcileCategory("panel", push=False, dataDir=str(tmp_path))
    assert out["push"] == 0
    assert called["up"] is False
    assert out["pull"] == 1


def test_reconcile_category_unknown_rejected() -> None:
    """미등록 category → ValueError."""
    from dartlab.pipeline import reconcile

    with pytest.raises(ValueError, match="unknown category"):
        reconcile.reconcileCategory("__nope__")


def test_reconcile_category_nested_rejected(monkeypatch) -> None:
    """nested 카테고리 → ValueError (flat 전용 가드)."""
    from dartlab.core.dataConfig import DATA_RELEASES
    from dartlab.pipeline import reconcile

    monkeypatch.setitem(DATA_RELEASES["panel"], "nested", True)
    with pytest.raises(ValueError, match="nested"):
        reconcile.reconcileCategory("panel")


def test_run_panel_reconcile_maps_summary(monkeypatch) -> None:
    """runPanelReconcile — reconcileCategory summary → StageResult(rows=pulled, uploaded=pushed)."""
    from dartlab.pipeline import reconcile as recmod
    from dartlab.pipeline.stages import reconcile as stage

    captured = {}

    def stub(dataCat, *, pull, push, token=None):
        captured["cat"] = dataCat
        captured["push"] = push
        return {"localBefore": 100, "remoteBefore": 90, "pull": 5, "push": 3, "pulled": 5, "pushed": 3, "inSync": False}

    monkeypatch.setattr(recmod, "reconcileCategory", stub)
    res = stage.runPanelReconcile(upload=True)
    assert res.rows == 5 and res.uploaded == 3 and res.report.ok == 1
    assert captured == {"cat": "panel", "push": True}


def test_run_edgar_panel_reconcile_maps_summary(monkeypatch) -> None:
    """runEdgarPanelReconcile — category=edgarPanel, upload=False→push=False."""
    from dartlab.pipeline import reconcile as recmod
    from dartlab.pipeline.stages import reconcile as stage

    captured = {}

    def stub(dataCat, *, pull, push, token=None):
        captured["cat"] = dataCat
        captured["push"] = push
        return {"localBefore": 1, "remoteBefore": 1, "pull": 0, "push": 0, "pulled": 0, "pushed": 0, "inSync": True}

    monkeypatch.setattr(recmod, "reconcileCategory", stub)
    stage.runEdgarPanelReconcile(upload=False)
    assert captured == {"cat": "edgarPanel", "push": False}


def test_run_reconcile_isolates_failure(monkeypatch) -> None:
    """reconcile 예외는 StageResult.report.err 로 격리."""
    from dartlab.pipeline import reconcile as recmod
    from dartlab.pipeline.stages import reconcile as stage

    def boom(*a, **k):
        raise RuntimeError("HF down")

    monkeypatch.setattr(recmod, "reconcileCategory", boom)
    res = stage.runPanelReconcile()
    assert res.report.err == 1 and res.report.ok == 0
    assert any("panelReconcile" in f for f in res.report.failures)


def test_reconcile_stages_registered() -> None:
    """buildRegistry 에 panelReconcile·edgarPanelReconcile 등록 + run 바인딩."""
    from dartlab.pipeline.registry import buildRegistry
    from dartlab.pipeline.stages.reconcile import runEdgarPanelReconcile, runPanelReconcile

    reg = buildRegistry()
    assert reg["panelReconcile"].run is runPanelReconcile
    assert reg["edgarPanelReconcile"].run is runEdgarPanelReconcile
    assert "panel" in reg["panelReconcile"].uploadCategories
    assert "edgarPanel" in reg["edgarPanelReconcile"].uploadCategories

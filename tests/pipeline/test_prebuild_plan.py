"""Data prebuild planning contracts."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]


def _loadScript(rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module
    spec.loader.exec_module(module)
    return module


def test_prebuild_base_seed_plan_is_cache_first():
    """Cached heavy categories must not reopen HF tree listing."""
    mod = _loadScript(".github/scripts/prebuild/planning/prebuildPlan.py")

    plan = mod.planBaseSeed({"finance": 2, "report": 0})

    assert plan.cachedCategories == ("finance",)
    assert plan.missingCategories == ("report",)


def test_prebuild_panel_bootstrap_records_remote_without_download():
    """First incremental run must not download every panel file."""
    mod = _loadScript(".github/scripts/prebuild/planning/prebuildPlan.py")

    plan = mod.planPanelDelta({}, {"dart/panel/005930.parquet": 11, "dart/panel/000660.parquet": 22})

    assert plan.bootstrap is True
    assert plan.processRel == ()
    assert plan.changedCodes == ()
    assert plan.newState == {"dart/panel/005930.parquet": 11, "dart/panel/000660.parquet": 22}


def test_prebuild_panel_delta_caps_without_marking_deferred_complete():
    """Capped changed files must stay in the old ledger state for next-cycle drain."""
    mod = _loadScript(".github/scripts/prebuild/planning/prebuildPlan.py")

    prior = {
        "dart/panel/000660.parquet": 1,
        "dart/panel/005930.parquet": 1,
        "dart/panel/035420.parquet": 1,
        "dart/panel/OLD.parquet": 1,
    }
    remote = {
        "dart/panel/000660.parquet": 2,
        "dart/panel/005930.parquet": 2,
        "dart/panel/035420.parquet": 2,
    }

    plan = mod.planPanelDelta(prior, remote, cap=2)

    assert plan.capped is True
    assert plan.processRel == ("dart/panel/000660.parquet", "dart/panel/005930.parquet")
    assert plan.deferredRel == ("dart/panel/035420.parquet",)
    assert plan.changedCodes == ("000660", "005930")
    assert plan.removedCodes == ("OLD",)
    assert plan.newState["dart/panel/000660.parquet"] == 2
    assert plan.newState["dart/panel/005930.parquet"] == 2
    assert plan.newState["dart/panel/035420.parquet"] == 1
    assert "dart/panel/OLD.parquet" not in plan.newState


def test_prebuild_scan_manifest_uses_fixed_artifacts():
    """Scan seeding should resolve known files directly instead of listing the tree."""
    mod = _loadScript(".github/scripts/prebuild/planning/prebuildManifest.py")

    rels = mod.scanArtifactRelPaths("dart/scan", ["dividend", "employee"])

    assert "dart/scan/finance.parquet" in rels
    assert "dart/scan/_scanBuildState.json" in rels
    assert "dart/scan/report/dividend.parquet" in rels
    assert "dart/scan/report/employee.parquet" in rels

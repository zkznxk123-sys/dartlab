from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.unit


def test_generate_intelligence_pack_has_required_sections():
    from scripts.build.generateSpec import generateIntelligencePack

    pack = json.loads(generateIntelligencePack())

    assert pack["schemaVersion"] == 1
    assert pack["sourceHash"]
    assert pack["generatedAt"]
    for key in (
        "apiMap",
        "capabilitySkillMap",
        "analysisGraph",
        "processMap",
        "dataCatalog",
        "recipeMap",
        "visualContract",
        "safetyPolicy",
    ):
        assert key in pack
    sample = pack["capabilitySkillMap"][0]
    for key in (
        "whenToUse",
        "questionTypes",
        "requiredInputs",
        "outputShape",
        "dataColumns",
        "freshness",
        "commonCalculations",
        "verification",
        "visualPolicy",
        "failureModes",
        "badUses",
    ):
        assert key in sample or any(key in row for row in pack["capabilitySkillMap"])


def test_intelligence_pack_loader_validates_bundled_pack():
    from dartlab.ai.runtime.intelligence_pack import loadIntelligencePack, packSummary

    pack = loadIntelligencePack()
    summary = packSummary(pack)

    assert pack["available"] is True
    assert summary["schemaVersion"] == 1
    assert summary["sourceHash"]
    assert summary["capabilityCount"] > 0


def test_intelligence_pack_search_prefers_krx_indices_for_index_strength():
    from dartlab.ai.runtime.intelligence_pack import searchIntelligencePack

    rows = searchIntelligencePack("최근 주가지수 강세", kind="data", limit=3)

    assert rows
    assert rows[0]["summary"] == "krx.indices"
    assert "BAS_DD" in rows[0]["detail"]
    assert "IDX_NM" in rows[0]["detail"]
    assert "FLUC_RT" in rows[0]["detail"]

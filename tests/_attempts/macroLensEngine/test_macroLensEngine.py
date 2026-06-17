from __future__ import annotations

from macroLensEngine import (
    bestLagRelation,
    buildAttemptSnapshot,
    buildSampleSeries,
    evaluateExposureQuality,
    loadJson,
)


def testRegistryHasRequiredDriversAndEdges() -> None:
    registry = loadJson("driverRegistry.sample.json")
    edges = loadJson("transmissionEdges.sample.json")
    driverIds = {row["id"] for row in registry["drivers"]}
    assert {"USDKRW", "BASE_RATE", "CPI", "EXPORT", "DCOILWTICO"} <= driverIds
    assert not ({row["driverId"] for row in edges["edges"]} - driverIds)
    sectors = {sector for row in edges["edges"] for sector in row["sectorKeys"] if sector != "all"}
    assert {"semiconductor", "auto", "bank", "chemical", "utility"} <= sectors


def testLagRelationFindsObservableCandidate() -> None:
    series = buildSampleSeries()
    relation = bestLagRelation("EXPORT", series["EXPORT"], series["targetReturn"], [0, 6])
    assert relation.nObs >= 48
    assert 0 <= relation.lagMonths <= 6
    assert relation.corr is not None
    assert relation.rSquared is not None
    assert relation.rSquared >= 0.12


def testQualityGateHidesBetaWhenCompanyEvidenceIsPartial() -> None:
    series = buildSampleSeries()
    relation = bestLagRelation("USDKRW", series["USDKRW"], series["targetReturn"], [0, 3])
    qualityGate = loadJson("exposureQuality.sample.json")["qualityGate"]
    quality = evaluateExposureQuality(
        relation,
        latestObservationDate="2026-05-28",
        priceAsOf="2026-05-31",
        requiredCompanyEvidence=["해외 매출 비중", "외화 매출·매입 통화", "FX 손익 주석"],
        availableCompanyEvidence={"해외 매출 비중"},
        qualityGate=qualityGate,
    )
    assert quality["status"] == "qualitativeOnly"
    assert quality["displayBeta"] is False
    assert quality["missingEvidence"]


def testQualityGateBlocksLookaheadAndStaleDriver() -> None:
    series = buildSampleSeries()
    relation = bestLagRelation("BASE_RATE", series["BASE_RATE"], series["targetReturn"], [3, 12])
    qualityGate = loadJson("exposureQuality.sample.json")["qualityGate"]
    lookahead = evaluateExposureQuality(
        relation,
        latestObservationDate="2026-06-28",
        priceAsOf="2026-05-31",
        requiredCompanyEvidence=["부채비율"],
        availableCompanyEvidence={"부채비율"},
        qualityGate=qualityGate,
    )
    stale = evaluateExposureQuality(
        relation,
        latestObservationDate="2025-12-28",
        priceAsOf="2026-05-31",
        requiredCompanyEvidence=["부채비율"],
        availableCompanyEvidence={"부채비율"},
        qualityGate=qualityGate,
    )
    assert lookahead["status"] == "blocked"
    assert "lookahead" in lookahead["blockedReasons"]
    assert stale["status"] == "blocked"
    assert "staleDriver" in stale["blockedReasons"]


def testAttemptSnapshotMatchesMacroLensContractShape() -> None:
    snapshot = buildAttemptSnapshot()
    assert snapshot["drivers"]
    assert snapshot["transmissionEdges"]
    assert snapshot["falsifiers"]
    assert snapshot["sourceRefs"]
    assert {row["readiness"]["status"] for row in snapshot["scenarios"]} <= {
        "ready",
        "needsEvidence",
        "blocked",
    }
    assert all("displayBeta" in quality for quality in snapshot["exposureQuality"].values())
    assert all("confidence" in edge for edge in snapshot["transmissionEdges"])
    for driver in snapshot["drivers"]:
        lineage = driver["sourceLineage"]
        assert lineage["source"]
        assert lineage["sourceSeriesId"] == driver["sourceSeriesId"]
        assert lineage["observationDate"]
        assert lineage["value"] is not None
        assert lineage["unit"] == driver["unit"]
        assert lineage["artifactPath"].startswith("macro/")

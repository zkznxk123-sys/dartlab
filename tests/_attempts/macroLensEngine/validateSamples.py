from __future__ import annotations

import json
from pathlib import Path

from macroLensEngine import buildAttemptSnapshot

ROOT = Path(__file__).resolve().parent


def load(name: str) -> dict:
    with (ROOT / name).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def require_keys(rows: list[dict], keys: set[str], label: str) -> None:
    for i, row in enumerate(rows):
        missing = sorted(keys - set(row))
        if missing:
            raise SystemExit(f"{label}[{i}] missing keys: {', '.join(missing)}")


def main() -> None:
    registry = load("driverRegistry.sample.json")
    edges = load("transmissionEdges.sample.json")
    quality = load("exposureQuality.sample.json")

    drivers = registry.get("drivers", [])
    require_keys(
        drivers,
        {
            "id",
            "source",
            "sourceSeriesId",
            "market",
            "unit",
            "transform",
            "directionSemantics",
            "defaultLagMonths",
            "releaseLagDays",
            "staleAfterDays",
            "requiredAsOfPolicy",
        },
        "drivers",
    )
    driver_ids = {d["id"] for d in drivers}
    if len(driver_ids) != len(drivers):
        raise SystemExit("duplicate driver id")
    required_drivers = {"USDKRW", "BASE_RATE", "CPI", "EXPORT", "DCOILWTICO"}
    missing_drivers = sorted(required_drivers - driver_ids)
    if missing_drivers:
        raise SystemExit(f"required drivers missing: {', '.join(missing_drivers)}")
    aliases = registry.get("aliases", {})
    bad_alias_targets = sorted({target for target in aliases.values()} - driver_ids)
    if bad_alias_targets:
        raise SystemExit(f"aliases reference unknown drivers: {', '.join(bad_alias_targets)}")
    if aliases.get("KRW_USD") != "USDKRW":
        raise SystemExit("KRW_USD alias must normalize to USDKRW")

    edge_rows = edges.get("edges", [])
    require_keys(
        edge_rows,
        {
            "id",
            "driverId",
            "market",
            "sectorKeys",
            "channel",
            "financialLine",
            "valuationLever",
            "sign",
            "lagMonths",
            "evidenceLevel",
            "confidence",
            "requiredCompanyEvidence",
            "falsifiers",
            "sourceRefs",
        },
        "edges",
    )
    unknown = sorted({e["driverId"] for e in edge_rows} - driver_ids)
    if unknown:
        raise SystemExit(f"edges reference unknown drivers: {', '.join(unknown)}")
    sectors = {sector for edge in edge_rows for sector in edge.get("sectorKeys", []) if sector != "all"}
    required_sectors = {"semiconductor", "auto", "bank", "chemical", "utility"}
    missing_sectors = sorted(required_sectors - sectors)
    if missing_sectors:
        raise SystemExit(f"required sectors missing: {', '.join(missing_sectors)}")
    for edge in edge_rows:
        if not edge["sourceRefs"]:
            raise SystemExit(f"edge {edge['id']} must include sourceRefs")

    gate = quality.get("qualityGate", {})
    require_keys(
        [gate],
        {
            "minimumObservations",
            "preferredObservations",
            "minimumAbsCorrelationForInfo",
            "minimumR2ForBetaDisplay",
            "maxStaleDays",
            "requiredCompanyEvidenceCoverage",
            "blockedStatuses",
        },
        "qualityGate",
    )
    if gate["minimumObservations"] > gate["preferredObservations"]:
        raise SystemExit("minimumObservations must not exceed preferredObservations")
    examples = quality.get("examples", [])
    require_keys(
        examples,
        {
            "companyCode",
            "driverId",
            "windowMonths",
            "lagMonths",
            "nObs",
            "corr",
            "rSquared",
            "coverage",
            "companyEvidenceCoverage",
            "missingEvidence",
            "status",
            "displayRule",
        },
        "quality.examples",
    )
    statuses = {row["status"] for row in examples}
    missing_statuses = sorted({"open", "qualitativeOnly", "blocked"} - statuses)
    if missing_statuses:
        raise SystemExit(f"quality examples missing statuses: {', '.join(missing_statuses)}")

    snapshot = buildAttemptSnapshot()
    if not snapshot["drivers"]:
        raise SystemExit("attempt snapshot has no drivers")
    require_keys(
        [row["sourceLineage"] for row in snapshot["drivers"]],
        {
            "source",
            "sourceSeriesId",
            "observationDate",
            "value",
            "unit",
            "artifactPath",
            "asOfPolicy",
        },
        "snapshot.drivers.sourceLineage",
    )
    if not snapshot["transmissionEdges"]:
        raise SystemExit("attempt snapshot has no transmission edges")
    if not all("confidence" in row for row in snapshot["transmissionEdges"]):
        raise SystemExit("transmission edges must include confidence")
    if not snapshot["scenarios"]:
        raise SystemExit("attempt snapshot has no scenarios")
    if not all("displayBeta" in row for row in snapshot["exposureQuality"].values()):
        raise SystemExit("exposure quality rows must include displayBeta")

    print("macroLensEngine sample contracts OK")


if __name__ == "__main__":
    main()

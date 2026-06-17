from __future__ import annotations

import json
from pathlib import Path

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

    edge_rows = edges.get("edges", [])
    require_keys(
        edge_rows,
        {
            "id",
            "driverId",
            "sectorKeys",
            "financialLine",
            "valuationLever",
            "sign",
            "lagMonths",
            "evidenceLevel",
            "confidenceFloor",
            "requiredCompanyEvidence",
            "falsifiers",
        },
        "edges",
    )
    unknown = sorted({e["driverId"] for e in edge_rows} - driver_ids)
    if unknown:
        raise SystemExit(f"edges reference unknown drivers: {', '.join(unknown)}")

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

    print("macroLensEngine sample contracts OK")


if __name__ == "__main__":
    main()

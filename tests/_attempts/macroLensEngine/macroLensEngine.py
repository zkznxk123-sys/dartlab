from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class SeriesPoint:
    date: str
    value: float


@dataclass(frozen=True)
class LagRelation:
    driverId: str
    lagMonths: int
    nObs: int
    corr: float | None
    rSquared: float | None
    window: str


def loadJson(name: str) -> dict[str, Any]:
    """Load one local Macro Lens attempt contract."""
    with (ROOT / name).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def parseDate(value: str) -> date:
    if len(value) == 8:
        value = f"{value[:4]}-{value[4:6]}-{value[6:8]}"
    return date.fromisoformat(value)


def monthKey(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}-28"


def addMonths(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = year * 12 + month - 1 + delta
    return idx // 12, idx % 12 + 1


def buildMonthlyDates(count: int, *, startYear: int = 2021, startMonth: int = 1) -> list[str]:
    return [monthKey(*addMonths(startYear, startMonth, i)) for i in range(count)]


def pearson(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    leftMean = sum(left) / len(left)
    rightMean = sum(right) / len(right)
    cov = sum((a - leftMean) * (b - rightMean) for a, b in zip(left, right))
    leftVar = sum((a - leftMean) ** 2 for a in left)
    rightVar = sum((b - rightMean) ** 2 for b in right)
    denom = math.sqrt(leftVar * rightVar)
    if denom <= 0:
        return None
    return cov / denom


def firstDiff(series: list[SeriesPoint]) -> list[SeriesPoint]:
    return [SeriesPoint(series[i].date, series[i].value - series[i - 1].value) for i in range(1, len(series))]


def zScore(values: list[float]) -> list[float]:
    if not values:
        return []
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / max(1, len(values) - 1)
    sd = math.sqrt(var)
    if sd <= 0:
        return [0.0 for _ in values]
    return [(v - mean) / sd for v in values]


def buildSampleSeries() -> dict[str, list[SeriesPoint]]:
    """Build deterministic fixture series for repeatable proof tests."""
    dates = buildMonthlyDates(65)
    raw: dict[str, list[float]] = {
        "USDKRW": [],
        "BASE_RATE": [],
        "CPI": [],
        "EXPORT": [],
        "DGS10": [],
        "BAMLH0A0HYM2": [],
        "DCOILWTICO": [],
    }
    for i in range(len(dates)):
        raw["USDKRW"].append(1080 + i * 2.2 + math.sin(i / 2.7) * 27)
        raw["BASE_RATE"].append(1.2 + min(i, 38) * 0.045 + math.sin(i / 5.5) * 0.08)
        raw["CPI"].append(1.4 + math.sin(i / 4.0) * 1.1 + (0.9 if 18 < i < 42 else 0.0))
        raw["EXPORT"].append(95 + i * 0.35 + math.sin(i / 3.0) * 7.5)
        raw["DGS10"].append(1.1 + i * 0.035 + math.cos(i / 4.2) * 0.22)
        raw["BAMLH0A0HYM2"].append(3.8 + math.sin(i / 3.7) * 0.55 + (0.8 if 24 < i < 32 else 0.0))
        raw["DCOILWTICO"].append(52 + math.sin(i / 3.2) * 14 + i * 0.18)

    series = {
        key: [SeriesPoint(dates[i], round(value, 6)) for i, value in enumerate(values)] for key, values in raw.items()
    }
    exportDiff = zScore([p.value for p in firstDiff(series["EXPORT"])])
    fxDiff = zScore([p.value for p in firstDiff(series["USDKRW"])])
    rateDiff = zScore([p.value for p in firstDiff(series["BASE_RATE"])])
    oilDiff = zScore([p.value for p in firstDiff(series["DCOILWTICO"])])
    target: list[SeriesPoint] = []
    for i in range(1, len(dates)):
        exportLag = exportDiff[i - 2] if i >= 2 else 0.0
        fxLag = fxDiff[i - 2] if i >= 2 else 0.0
        rateLag = rateDiff[i - 5] if i >= 5 else 0.0
        oilLag = oilDiff[i - 2] if i >= 2 else 0.0
        cycleNoise = math.sin(i * 1.7) * 0.012 + math.cos(i / 2.9) * 0.006
        value = 0.018 * exportLag + 0.011 * fxLag - 0.012 * rateLag - 0.006 * oilLag + cycleNoise
        target.append(SeriesPoint(dates[i], round(value, 6)))
    series["targetReturn"] = target
    return series


def bestLagRelation(
    driverId: str,
    driverSeries: list[SeriesPoint],
    targetSeries: list[SeriesPoint],
    lagMonths: list[int] | tuple[int, int],
) -> LagRelation:
    """Return the strongest bounded lagged co-movement candidate."""
    if len(lagMonths) == 2:
        lags = list(range(int(lagMonths[0]), int(lagMonths[1]) + 1))
    else:
        lags = [int(x) for x in lagMonths]
    driverDiff = firstDiff(driverSeries)
    targetByDate = {p.date: p.value for p in targetSeries}
    best: LagRelation | None = None
    for lag in lags:
        left: list[float] = []
        right: list[float] = []
        alignedDates: list[str] = []
        for i, point in enumerate(driverDiff):
            targetIdx = i + lag
            if targetIdx >= len(driverDiff):
                continue
            targetDate = driverDiff[targetIdx].date
            if targetDate not in targetByDate:
                continue
            left.append(point.value)
            right.append(targetByDate[targetDate])
            alignedDates.append(targetDate)
        corr = pearson(left, right)
        rSquared = None if corr is None else corr * corr
        window = f"{alignedDates[0]}..{alignedDates[-1]}" if alignedDates else "empty"
        relation = LagRelation(
            driverId=driverId,
            lagMonths=lag,
            nObs=len(left),
            corr=None if corr is None else round(corr, 4),
            rSquared=None if rSquared is None else round(rSquared, 4),
            window=window,
        )
        if best is None:
            best = relation
        else:
            oldScore = -1 if best.corr is None else abs(best.corr)
            newScore = -1 if relation.corr is None else abs(relation.corr)
            if newScore > oldScore:
                best = relation
    return best or LagRelation(driverId, 0, 0, None, None, "empty")


def evidenceCoverage(required: list[str], available: set[str]) -> tuple[float, list[str]]:
    if not required:
        return 1.0, []
    missing = [item for item in required if item not in available]
    return (len(required) - len(missing)) / len(required), missing


def staleDays(observationDate: str, priceAsOf: str) -> int:
    return (parseDate(priceAsOf) - parseDate(observationDate)).days


def evaluateExposureQuality(
    relation: LagRelation,
    *,
    latestObservationDate: str,
    priceAsOf: str,
    requiredCompanyEvidence: list[str],
    availableCompanyEvidence: set[str],
    qualityGate: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate open, qualitative-only, or blocked exposure quality."""
    coverage, missingEvidence = evidenceCoverage(requiredCompanyEvidence, availableCompanyEvidence)
    latestDate = parseDate(latestObservationDate)
    priceDate = parseDate(priceAsOf)
    blockedReasons: list[str] = []
    weakReasons: list[str] = []
    if latestDate > priceDate:
        blockedReasons.append("lookahead")
    days = staleDays(latestObservationDate, priceAsOf)
    if days > int(qualityGate["maxStaleDays"]):
        blockedReasons.append("staleDriver")
    if relation.nObs == 0:
        blockedReasons.append("missingPriceOverlap")
    elif relation.nObs < int(qualityGate["minimumObservations"]):
        weakReasons.append("lowN")
    rSquared = relation.rSquared or 0.0
    if rSquared < float(qualityGate["minimumR2ForBetaDisplay"]):
        weakReasons.append("lowR2")
    if coverage <= 0:
        blockedReasons.append("missingCompanyEvidence")
    elif coverage < float(qualityGate["requiredCompanyEvidenceCoverage"]):
        weakReasons.append("partialCompanyEvidence")

    if blockedReasons:
        status = "blocked"
    elif weakReasons:
        status = "qualitativeOnly"
    else:
        status = "open"
    reasonParts = blockedReasons or weakReasons or ["qualityGateOpen"]
    return {
        "status": status,
        "reason": ", ".join(reasonParts),
        "nObs": relation.nObs,
        "corr": relation.corr,
        "rSquared": relation.rSquared,
        "window": relation.window,
        "lagMonths": relation.lagMonths,
        "coverage": "company" if coverage >= 1 else "sectorAndPartialCompany" if coverage > 0 else "missing",
        "evidenceCoverage": round(coverage, 3),
        "missingEvidence": missingEvidence,
        "displayBeta": status == "open",
        "blockedReasons": blockedReasons,
        "weakReasons": weakReasons,
        "staleDays": days,
    }


def driverPriority(relation: LagRelation, quality: dict[str, Any], relevance: str) -> str:
    relevanceScore = {"primary": 36, "secondary": 24, "context": 10}.get(relevance, 10)
    corrScore = 0 if relation.corr is None else min(28, abs(relation.corr) * 40)
    rSquaredScore = 0 if relation.rSquared is None else min(22, relation.rSquared * 85)
    gatePenalty = -35 if quality["status"] == "blocked" else -8 if quality["status"] == "qualitativeOnly" else 8
    score = max(0, min(100, round(relevanceScore + corrScore + rSquaredScore + gatePenalty)))
    if quality["status"] == "blocked":
        level = "blocked"
    elif score >= 70:
        level = "high"
    elif score >= 45:
        level = "medium"
    else:
        level = "low"
    return level


def scenarioReadiness(driverQuality: dict[str, Any]) -> dict[str, str]:
    if driverQuality["status"] == "open":
        return {"status": "ready", "reason": "quality gate open; beta display allowed"}
    if driverQuality["status"] == "qualitativeOnly":
        return {"status": "needsEvidence", "reason": driverQuality["reason"]}
    return {"status": "blocked", "reason": driverQuality["reason"]}


def buildAttemptSnapshot(
    *,
    sectorKey: str = "semiconductor",
    priceAsOf: str = "2026-05-31",
    availableCompanyEvidence: set[str] | None = None,
) -> dict[str, Any]:
    """Build a MacroLensSnapshot-compatible proof payload."""
    available = availableCompanyEvidence or {"수출 매출", "재고", "주요 제품 수요", "부채비율", "이자보상배율"}
    registry = loadJson("driverRegistry.sample.json")
    edgeDoc = loadJson("transmissionEdges.sample.json")
    qualityGate = loadJson("exposureQuality.sample.json")["qualityGate"]
    series = buildSampleSeries()
    driversById = {row["id"]: row for row in registry["drivers"]}
    selectedEdges = [row for row in edgeDoc["edges"] if "all" in row["sectorKeys"] or sectorKey in row["sectorKeys"]]
    latestDates = {key: values[-1].date for key, values in series.items() if key != "targetReturn"}
    qualityByDriver: dict[str, dict[str, Any]] = {}
    driverRows: dict[str, dict[str, Any]] = {}
    transformedEdges: list[dict[str, Any]] = []
    falsifiers: list[dict[str, Any]] = []
    for edge in selectedEdges:
        driverId = edge["driverId"]
        if driverId not in driversById or driverId not in series:
            falsifiers.append(
                {
                    "type": "missingDriver",
                    "driverId": driverId,
                    "severity": "blocker",
                    "detail": "driver registry or sample series missing",
                }
            )
            continue
        relation = bestLagRelation(driverId, series[driverId], series["targetReturn"], edge["lagMonths"])
        quality = evaluateExposureQuality(
            relation,
            latestObservationDate=latestDates[driverId],
            priceAsOf=priceAsOf,
            requiredCompanyEvidence=edge["requiredCompanyEvidence"],
            availableCompanyEvidence=available,
            qualityGate=qualityGate,
        )
        qualityByDriver[driverId] = quality
        priorityLevel = driverPriority(relation, quality, "primary" if sectorKey in edge["sectorKeys"] else "secondary")
        driver = driversById[driverId]
        latestPoint = series[driverId][-1]
        sourceLineage = {
            "source": driver["source"],
            "sourceSeriesId": driver["sourceSeriesId"],
            "observationDate": latestDates[driverId],
            "value": latestPoint.value,
            "unit": driver["unit"],
            "artifactPath": f"macro/{driver['source'].lower()}/observations.parquet",
            "asOfPolicy": driver["requiredAsOfPolicy"],
        }
        driverRows[driverId] = {
            "id": driverId,
            "labelKr": driver["labelKr"],
            "market": driver["market"],
            "source": driver["source"],
            "sourceSeriesId": driver["sourceSeriesId"],
            "unit": driver["unit"],
            "transform": driver["transform"],
            "directionSemantics": driver["directionSemantics"],
            "defaultLagMonths": driver["defaultLagMonths"],
            "latestObservationDate": latestDates[driverId],
            "latestValue": latestPoint.value,
            "sourceLineage": sourceLineage,
            "priorityLevel": priorityLevel,
            "relation": relation.__dict__,
            "quality": quality,
        }
        transformedEdges.append(
            {
                "id": edge["id"],
                "driverId": driverId,
                "sectorKey": sectorKey if "all" not in edge["sectorKeys"] else "all",
                "financialLine": edge["financialLine"],
                "valuationLever": edge["valuationLever"],
                "sign": edge["sign"],
                "lagMonths": edge["lagMonths"],
                "evidenceLevel": edge["evidenceLevel"],
                "confidence": edge["confidence"],
                "requiredCompanyEvidence": edge["requiredCompanyEvidence"],
                "missingCompanyEvidence": quality["missingEvidence"],
                "qualityStatus": quality["status"],
                "sourceRefs": [*edge["sourceRefs"], sourceLineage["artifactPath"], "exposureQuality.sample.json"],
            }
        )
        if quality["status"] != "open":
            falsifiers.append(
                {
                    "type": "exposureQuality",
                    "driverId": driverId,
                    "severity": "blocker" if quality["status"] == "blocked" else "warning",
                    "detail": quality["reason"],
                }
            )

    scenarios = []
    for scenario in [
        {"id": "fx10", "driverId": "USDKRW", "shock": "USDKRW +10%"},
        {"id": "rate100", "driverId": "BASE_RATE", "shock": "BASE_RATE +100bp"},
        {"id": "exportDown", "driverId": "EXPORT", "shock": "EXPORT YoY -10%"},
        {"id": "oil30", "driverId": "DCOILWTICO", "shock": "WTI +30%"},
    ]:
        quality = qualityByDriver.get(scenario["driverId"])
        readiness = (
            scenarioReadiness(quality) if quality else {"status": "blocked", "reason": "driver edge unavailable"}
        )
        scenarios.append({**scenario, "readiness": readiness})

    return {
        "asOf": {"price": priceAsOf, "macro": max(latestDates.values()) if latestDates else None},
        "drivers": sorted(
            driverRows.values(), key=lambda row: {"high": 0, "medium": 1, "low": 2, "blocked": 3}[row["priorityLevel"]]
        ),
        "transmissionEdges": transformedEdges,
        "exposureQuality": qualityByDriver,
        "falsifiers": falsifiers,
        "scenarios": scenarios,
        "sourceRefs": [
            "driverRegistry.sample.json",
            "transmissionEdges.sample.json",
            "exposureQuality.sample.json",
            "macro/{ecos,fred}/observations.parquet source/date/value fixture",
        ],
        "missing": sorted({item for row in qualityByDriver.values() for item in row["missingEvidence"]}),
    }


def main() -> None:
    snapshot = buildAttemptSnapshot()
    print(json.dumps(snapshot, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

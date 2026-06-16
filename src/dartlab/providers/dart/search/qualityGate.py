"""Query-log gold and miss-ledger gates for product search."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

REAL_GOLD_ORIGINS = {"real", "operator", "operatorReal", "userLog", "production"}
REVIEWED_STATUSES = {"reviewed", "approved", "accepted", "gold"}
DEFAULT_REQUIRED_TARGETS = ("filing", "news", "noAnswer")


def loadQueryGold(path: str | Path) -> list[dict[str, Any]]:
    """Load query-log gold rows from JSON or JSONL.

    Args:
        path: Gold file path. JSON arrays, ``{"rows": [...]}``, and JSONL are supported.

    Returns:
        list[dict[str, Any]]: Gold rows in file order.

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the file shape is unsupported.

    Example:
        >>> callable(loadQueryGold)
        True
    """
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    data = json.loads(text) if text.strip() else []
    if isinstance(data, list):
        return [dict(row) for row in data]
    if isinstance(data, dict):
        rows = data.get("rows") or data.get("gold") or data.get("queryLogGold")
        if isinstance(rows, list):
            return [dict(row) for row in rows]
    raise ValueError(f"unsupported query gold shape: {p}")


def evaluateQueryGoldRows(
    goldRows: Iterable[Mapping[str, Any]],
    resultsByQuery: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    minRows: int = 100,
    requiredTargets: Iterable[str] = DEFAULT_REQUIRED_TARGETS,
    requireRealReviewed: bool = True,
    thresholds: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Evaluate product search results against query-log gold.

    Args:
        goldRows: Iterable of query gold rows.
        resultsByQuery: Mapping from query text to ranked result rows.
        minRows: Minimum real reviewed rows required for release eligibility.
        requiredTargets: Target kinds that must be represented.
        requireRealReviewed: True blocks release if rows are proxy/generated/unreviewed.
        thresholds: Optional metric thresholds overriding defaults.

    Returns:
        dict[str, Any]: Metrics, blockers, and release eligibility.

    Raises:
        None.

    Example:
        >>> evaluateQueryGoldRows([], {}, minRows=0)["totalRows"]
        0
    """
    rows = [dict(row) for row in goldRows]
    targetCounts: dict[str, int] = {}
    originCounts: dict[str, int] = {}
    reviewCounts: dict[str, int] = {}
    docHit10Hits = 0
    docHit10Rows = 0
    top3Hits = 0
    top3Rows = 0
    readyRows = 0
    newsPrecisionSum = 0.0
    newsPrecisionRows = 0
    noAnswerRows = 0
    noAnswerFalseAccepts = 0

    rowEvaluations: list[dict[str, Any]] = []
    for gold in rows:
        query = str(gold.get("query") or "")
        target = normalizeTargetKind(gold)
        targetCounts[target] = targetCounts.get(target, 0) + 1
        origin = str(gold.get("goldOrigin") or "")
        review = str(gold.get("reviewStatus") or "")
        originCounts[origin] = originCounts.get(origin, 0) + 1
        reviewCounts[review] = reviewCounts.get(review, 0) + 1
        results = [dict(row) for row in _resultsForGold(gold, resultsByQuery)]
        if target == "noAnswer":
            noAnswerRows += 1
            falseAccept = any(_isAnswerable(row) for row in results[:10])
            if falseAccept:
                noAnswerFalseAccepts += 1
            else:
                readyRows += 1
            rowEvaluations.append(
                {
                    "query": query,
                    "target": target,
                    "ready": not falseAccept,
                    "falseAccept": falseAccept,
                    "docHit10": None,
                    "memoryCitationTop3Exact": None,
                    "newsSourcePrecision10": None,
                }
            )
            continue

        docHit10Rows += 1
        top3Rows += 1
        hit10 = _anyExpectedMatch(gold, results[:10])
        hit3 = _anyExpectedMatch(gold, results[:3])
        if hit10:
            docHit10Hits += 1
            readyRows += 1
        if hit3:
            top3Hits += 1
        precision = None
        if target == "news":
            newsPrecisionRows += 1
            precision = _sourcePrecision(results[:10], expectedSource="news")
            newsPrecisionSum += precision
        rowEvaluations.append(
            {
                "query": query,
                "target": target,
                "ready": hit10,
                "falseAccept": None,
                "docHit10": hit10,
                "memoryCitationTop3Exact": hit3,
                "newsSourcePrecision10": precision,
            }
        )

    metricThresholds = _thresholds(thresholds)
    totalRows = len(rows)
    realReviewedRows = sum(1 for row in rows if _isRealReviewed(row))
    metrics = {
        "overallReadyRate": _ratio(readyRows, totalRows),
        "docHit10": _ratio(docHit10Hits, docHit10Rows),
        "memoryCitationTop3Exact": _ratio(top3Hits, top3Rows),
        "newsSourcePrecision10": _ratio(newsPrecisionSum, newsPrecisionRows),
        "noAnswerFalseAcceptRate": _ratio(noAnswerFalseAccepts, noAnswerRows),
        "noAnswerNegativeRejectRate": _ratio(noAnswerRows - noAnswerFalseAccepts, noAnswerRows),
    }
    blockers = _releaseBlockers(
        rows=rows,
        targetCounts=targetCounts,
        realReviewedRows=realReviewedRows,
        minRows=minRows,
        requiredTargets=requiredTargets,
        requireRealReviewed=requireRealReviewed,
        metrics=metrics,
        thresholds=metricThresholds,
    )
    return {
        "totalRows": totalRows,
        "realReviewedRows": realReviewedRows,
        "coverageByKind": targetCounts,
        "goldOriginCounts": originCounts,
        "reviewStatusCounts": reviewCounts,
        "metrics": metrics,
        "metricsByKind": _metricsByKind(rowEvaluations),
        "thresholds": metricThresholds,
        "releaseEligible": not blockers,
        "blockers": blockers,
        "rows": rowEvaluations,
    }


def buildMissLedgerRows(
    goldRows: Iterable[Mapping[str, Any]],
    resultsByQuery: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    """Build a policy-oriented miss ledger from query-log gold results.

    Args:
        goldRows: Iterable of query gold rows.
        resultsByQuery: Mapping from query text to ranked result rows.

    Returns:
        list[dict[str, Any]]: Rows requiring review or product-policy work.

    Raises:
        None.

    Example:
        >>> buildMissLedgerRows([], {})
        []
    """
    misses: list[dict[str, Any]] = []
    for gold in goldRows:
        row = dict(gold)
        query = str(row.get("query") or "")
        target = normalizeTargetKind(row)
        results = [dict(result) for result in _resultsForGold(row, resultsByQuery)]
        topRefs = [_sourceRef(result) for result in results[:10] if _sourceRef(result)]
        failureTypes = _rowFailureTypes(row, results)
        if not _isRealReviewed(row):
            failureTypes.append("goldReviewRequired")
        for failureType in _dedupe(failureTypes):
            misses.append(
                {
                    "query": query,
                    "targetKind": target,
                    "expectedSourceRef": _expectedSourceRefText(row),
                    "expectedRceptNo": str(row.get("rceptNo") or row.get("rcept_no") or ""),
                    "topSourceRefs": topRefs,
                    "topSources": [str(result.get("source") or "") for result in results[:10]],
                    "failureType": failureType,
                    "sourceDataAsOf": str((results[0].get("dataAsOf") if results else "") or ""),
                    "decision": "blockRelease" if failureType != "goldReviewRequired" else "reviewGold",
                    "policyCandidate": _policyCandidate(failureType),
                    "reviewStatus": str(row.get("reviewStatus") or ""),
                    "goldOrigin": str(row.get("goldOrigin") or ""),
                }
            )
    return misses


def writeMissLedger(path: str | Path, rows: Iterable[Mapping[str, Any]]) -> None:
    """Write a JSONL miss ledger.

    Args:
        path: Output path.
        rows: Miss ledger rows.

    Returns:
        None.

    Raises:
        OSError: If the file cannot be written.

    Example:
        >>> callable(writeMissLedger)
        True
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(dict(row), ensure_ascii=False, sort_keys=True) for row in rows]
    p.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def normalizeTargetKind(row: Mapping[str, Any]) -> str:
    """Normalize a query-log target kind.

    Args:
        row: Query gold row.

    Returns:
        str: Normalized target kind.

    Raises:
        None.

    Example:
        >>> normalizeTargetKind({"target": "allFilings"})
        'filing'
    """
    target = str(row.get("targetKind") or row.get("target") or row.get("kind") or "").strip()
    aliases = {
        "allFilings": "filing",
        "dart": "filing",
        "dartPanel": "filing",
        "panel": "filing",
        "edgarPanel": "edgar",
        "edgar-panel": "edgar",
        "negative": "noAnswer",
        "no-answer": "noAnswer",
        "noanswer": "noAnswer",
    }
    return aliases.get(target, target or "filing")


def _releaseBlockers(
    *,
    rows: Sequence[Mapping[str, Any]],
    targetCounts: Mapping[str, int],
    realReviewedRows: int,
    minRows: int,
    requiredTargets: Iterable[str],
    requireRealReviewed: bool,
    metrics: Mapping[str, float],
    thresholds: Mapping[str, float],
) -> list[str]:
    blockers: list[str] = []
    if len(rows) < minRows:
        blockers.append(f"minRows:{len(rows)}/{minRows}")
    if requireRealReviewed and realReviewedRows < minRows:
        blockers.append(f"realReviewedRows:{realReviewedRows}/{minRows}")
    for target in requiredTargets:
        normalized = normalizeTargetKind({"target": target})
        if targetCounts.get(normalized, 0) == 0:
            blockers.append(f"missingTarget:{normalized}")
    if requireRealReviewed:
        proxyCount = sum(1 for row in rows if not _isRealOrigin(row))
        unreviewedCount = sum(1 for row in rows if not _isReviewed(row))
        if proxyCount:
            blockers.append(f"proxyGoldRows:{proxyCount}")
        if unreviewedCount:
            blockers.append(f"unreviewedGoldRows:{unreviewedCount}")
    for metric, minimum in thresholds.items():
        if _skipMetricThreshold(metric, targetCounts):
            continue
        value = metrics.get(metric, 0.0)
        if metric.endswith("FalseAcceptRate"):
            if value > minimum:
                blockers.append(f"metric:{metric}:{value:.4f}>{minimum:.4f}")
        elif value < minimum:
            blockers.append(f"metric:{metric}:{value:.4f}<{minimum:.4f}")
    return blockers


def _skipMetricThreshold(metric: str, targetCounts: Mapping[str, int]) -> bool:
    docTargets = sum(count for target, count in targetCounts.items() if target != "noAnswer")
    if metric in {"docHit10", "memoryCitationTop3Exact"}:
        return docTargets <= 0
    if metric == "newsSourcePrecision10":
        return int(targetCounts.get("news") or 0) <= 0
    if metric == "noAnswerFalseAcceptRate":
        return int(targetCounts.get("noAnswer") or 0) <= 0
    return False


def _thresholds(overrides: Mapping[str, float] | None) -> dict[str, float]:
    base = {
        "overallReadyRate": 0.9,
        "docHit10": 0.9,
        "memoryCitationTop3Exact": 0.9,
        "newsSourcePrecision10": 0.9,
        "noAnswerFalseAcceptRate": 0.1,
    }
    if overrides:
        base.update({str(k): float(v) for k, v in overrides.items()})
    return base


def _rowFailureTypes(gold: Mapping[str, Any], results: Sequence[Mapping[str, Any]]) -> list[str]:
    target = normalizeTargetKind(gold)
    if target == "noAnswer":
        return ["falseAccept"] if any(_isAnswerable(row) for row in results[:10]) else []
    failures = []
    if not results:
        failures.append("missingResults")
    if not _anyExpectedMatch(gold, results[:10]):
        failures.append("docMiss10")
        failures.extend(_topResultFailureTypes(results[:10]))
    elif not _anyExpectedMatch(gold, results[:3]):
        failures.append("citationMissTop3")
        failures.extend(_topResultFailureTypes(results[:3]))
    if target == "news" and _sourcePrecision(results[:10], expectedSource="news") < 1.0:
        failures.append("newsSourcePrecision10")
        failures.append("sourceIntentMiss")
    return failures


def _resultsForGold(
    gold: Mapping[str, Any], resultsByQuery: Mapping[str, Sequence[Mapping[str, Any]]]
) -> Sequence[Mapping[str, Any]]:
    for key in _goldResultKeys(gold):
        if key in resultsByQuery:
            return resultsByQuery.get(key) or []
    return []


def _goldResultKeys(gold: Mapping[str, Any]) -> list[str]:
    keys: list[str] = []
    for field in ("query", "queryId", "id"):
        key = str(gold.get(field) or "").strip()
        if key and key not in keys:
            keys.append(key)
    return keys


def _anyExpectedMatch(gold: Mapping[str, Any], results: Sequence[Mapping[str, Any]]) -> bool:
    refs = _expectedSourceRefs(gold)
    rceptNo = str(gold.get("rceptNo") or gold.get("rcept_no") or "").strip()
    title = str(gold.get("title") or "").strip()
    if not refs and not rceptNo and not title:
        return False
    for row in results:
        if not _isAnswerable(row):
            continue
        ref = _sourceRef(row)
        if refs and ref in refs:
            return True
        if rceptNo and (str(row.get("rcept_no") or "") == rceptNo or rceptNo in ref):
            return True
        if title and str(row.get("title") or row.get("section_title") or "") == title:
            return True
    return False


def _expectedSourceRefs(gold: Mapping[str, Any]) -> set[str]:
    refs: set[str] = set()
    value = gold.get("expectedSourceRefs") or gold.get("expectedSourceRef")
    if isinstance(value, str):
        refs.add(value)
    elif isinstance(value, Sequence):
        refs.update(str(item) for item in value if item)
    sourceRef = str(gold.get("sourceRef") or "").strip()
    if sourceRef:
        refs.add(sourceRef)
    return refs


def _expectedSourceRefText(gold: Mapping[str, Any]) -> str:
    refs = sorted(_expectedSourceRefs(gold))
    return ",".join(refs)


def _sourcePrecision(results: Sequence[Mapping[str, Any]], *, expectedSource: str) -> float:
    if not results:
        return 0.0
    matched = sum(1 for row in results if str(row.get("source") or "") == expectedSource)
    return matched / len(results)


def _sourceRef(row: Mapping[str, Any]) -> str:
    return str(row.get("sourceRef") or row.get("rcept_no") or "")


def _isAnswerable(row: Mapping[str, Any]) -> bool:
    value = row.get("answerable")
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return True
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "no", "n"}
    return bool(value)


def _isRealReviewed(row: Mapping[str, Any]) -> bool:
    return _isRealOrigin(row) and _isReviewed(row)


def _isRealOrigin(row: Mapping[str, Any]) -> bool:
    return str(row.get("goldOrigin") or "") in REAL_GOLD_ORIGINS


def _isReviewed(row: Mapping[str, Any]) -> bool:
    return str(row.get("reviewStatus") or "") in REVIEWED_STATUSES


def _policyCandidate(failureType: str) -> str:
    return {
        "docMiss10": "rankingOrFacetPolicy",
        "citationMissTop3": "rerankWindowOrCitationPolicy",
        "falseAccept": "negativeAnswerabilityPolicy",
        "missingResults": "sourceFreshnessOrCoveragePolicy",
        "newsSourcePrecision10": "sourceIntentPolicy",
        "sourceIntentMiss": "sourceIntentPolicy",
        "entityFacetMiss": "facetPlannerPolicy",
        "dateFacetMiss": "facetPlannerPolicy",
        "reportFacetMiss": "facetPlannerPolicy",
        "bodyEvidenceMiss": "evidencePackPolicy",
        "staleSource": "sourceFreshnessOrCoveragePolicy",
        "goldReviewRequired": "queryGoldReview",
    }.get(failureType, "policyReview")


def _metricsByKind(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        target = str(row.get("target") or "")
        grouped.setdefault(target, []).append(row)
    out: dict[str, dict[str, Any]] = {}
    for target, items in grouped.items():
        ready = sum(1 for item in items if item.get("ready") is True)
        docRows = [item for item in items if item.get("docHit10") is not None]
        top3Rows = [item for item in items if item.get("memoryCitationTop3Exact") is not None]
        falseAcceptRows = [item for item in items if item.get("falseAccept") is not None]
        newsRows = [item for item in items if item.get("newsSourcePrecision10") is not None]
        out[target] = {
            "rows": len(items),
            "readyRate": _ratio(ready, len(items)),
            "docHit10": _ratio(sum(1 for item in docRows if item.get("docHit10") is True), len(docRows)),
            "memoryCitationTop3Exact": _ratio(
                sum(1 for item in top3Rows if item.get("memoryCitationTop3Exact") is True),
                len(top3Rows),
            ),
            "falseAcceptRate": _ratio(
                sum(1 for item in falseAcceptRows if item.get("falseAccept") is True),
                len(falseAcceptRows),
            ),
            "newsSourcePrecision10": _ratio(
                sum(float(item.get("newsSourcePrecision10") or 0.0) for item in newsRows),
                len(newsRows),
            ),
        }
    return out


def _topResultFailureTypes(results: Sequence[Mapping[str, Any]]) -> list[str]:
    out: list[str] = []
    for row in results:
        reason = str(row.get("notAnswerableReason") or "")
        if not reason:
            continue
        if "source" in reason.lower():
            out.append("sourceIntentMiss")
        if "facetMismatch:company" in reason or "facetMismatch:corp" in reason:
            out.append("entityFacetMiss")
        if "facetMismatch:date" in reason:
            out.append("dateFacetMiss")
        if "facetMismatch:report" in reason or "facetMismatch:receipt" in reason:
            out.append("reportFacetMiss")
        if reason in {"missingSourceRef", "missingSnippet", "missingDataAsOf"}:
            out.append("bodyEvidenceMiss")
        if reason == "staleSource":
            out.append("staleSource")
    return out


def _ratio(numerator: float, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator)


def _dedupe(values: Iterable[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        if value not in out:
            out.append(value)
    return out

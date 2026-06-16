"""Query-log gold normalization for product search operations."""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from dartlab.providers.dart.search.qualityGate import REAL_GOLD_ORIGINS, REVIEWED_STATUSES, normalizeTargetKind

DEFAULT_REQUIRED_TARGETS = ("filing", "news", "noAnswer", "edgar")
QUERY_LOG_ENV = "DARTLAB_SEARCH_QUERY_LOG"
QUERY_LOG_TOPK_ENV = "DARTLAB_SEARCH_QUERY_LOG_TOPK"
DEFAULT_QUERY_LOG_REL = Path("search") / "queryLogRaw.jsonl"


def queryLogPathFromEnv() -> Path | None:
    """Resolve the optional raw query-log path from environment.

    Args:
        None.

    Returns:
        Path | None: None when query logging is disabled. ``1``/``true`` uses
        ``{dartlab.dataDir}/search/queryLogRaw.jsonl``; other values are paths.

    Raises:
        None.

    Example:
        >>> queryLogPathFromEnv() is None or isinstance(queryLogPathFromEnv(), Path)
        True
    """
    raw = os.environ.get(QUERY_LOG_ENV, "").strip()
    if not raw or raw.lower() in {"0", "false", "no", "off"}:
        return None
    if raw.lower() in {"1", "true", "yes", "on"}:
        import dartlab.config as _cfg

        return Path(_cfg.dataDir) / DEFAULT_QUERY_LOG_REL
    return Path(raw)


def buildRawQueryLogEvent(
    *,
    query: str,
    params: Mapping[str, Any],
    results: Sequence[Mapping[str, Any]],
    topK: int | None = None,
) -> dict[str, Any]:
    """Build one raw search query event for later reviewer labeling.

    Args:
        query: User query text.
        params: Search call parameters, such as scope/corp/date/limit.
        results: Ranked result rows after product-result normalization.
        topK: Number of top rows to persist. None reads
            ``DARTLAB_SEARCH_QUERY_LOG_TOPK`` or defaults to 10.

    Returns:
        dict[str, Any]: JSON-serializable raw query-log candidate row.

    Raises:
        None.

    Example:
        >>> event = buildRawQueryLogEvent(query="q", params={"scope": "auto"}, results=[])
        >>> event["query"]
        'q'
    """
    limit = _queryLogTopK(topK)
    topResults = [_projectResultRow(row) for row in list(results)[:limit]]
    event = {
        "queryId": _queryEventId(query, params),
        "query": str(query or ""),
        "observedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "goldOrigin": "userLog",
        "reviewStatus": "candidate",
        "params": {str(key): value for key, value in params.items() if value not in (None, "")},
        "topSourceRefs": [row["sourceRef"] for row in topResults if row.get("sourceRef")],
        "topSources": [row["source"] for row in topResults if row.get("source")],
        "topResults": topResults,
        "answerableCountTopK": sum(1 for row in topResults if row.get("answerable") is True),
        "dataAsOfBySource": _dataAsOfBySource(topResults),
    }
    if topResults:
        event["topSourceRef"] = topResults[0].get("sourceRef", "")
    return event


def appendRawQueryLogEvent(path: str | Path, event: Mapping[str, Any]) -> None:
    """Append one raw query-log event as JSONL.

    Args:
        path: Destination JSONL file.
        event: Event built by ``buildRawQueryLogEvent``.

    Returns:
        None.

    Raises:
        OSError: If the file cannot be written.
        TypeError: If the event is not JSON serializable.

    Example:
        >>> callable(appendRawQueryLogEvent)
        True
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(dict(event), ensure_ascii=False, sort_keys=True))
        f.write("\n")


def recordRawQueryLogEvent(
    *,
    query: str,
    params: Mapping[str, Any],
    results: Sequence[Mapping[str, Any]],
    path: str | Path | None = None,
    topK: int | None = None,
) -> dict[str, Any] | None:
    """Record a raw query-log event when a destination is configured.

    Args:
        query: User query text.
        params: Search call parameters.
        results: Ranked result rows.
        path: Explicit output path. None resolves ``DARTLAB_SEARCH_QUERY_LOG``.
        topK: Number of top rows to persist.

    Returns:
        dict[str, Any] | None: Written event, or None when logging is disabled.

    Raises:
        OSError: If logging is enabled but the event cannot be written.
        TypeError: If the event is not JSON serializable.

    Example:
        >>> recordRawQueryLogEvent(query="q", params={}, results=[], path=None) is None
        True
    """
    target = Path(path) if path is not None else queryLogPathFromEnv()
    if target is None:
        return None
    event = buildRawQueryLogEvent(query=query, params=params, results=results, topK=topK)
    appendRawQueryLogEvent(target, event)
    return event


def buildReviewerLabelTemplateRows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Build reviewer-label scaffold rows from raw query-log candidates.

    Args:
        rows: Raw query-log candidate rows.

    Returns:
        list[dict[str, Any]]: Label rows with candidate refs preserved but
        expected refs intentionally blank until a reviewer confirms them.

    Raises:
        None.

    Example:
        >>> buildReviewerLabelTemplateRows([{"query": "q"}])[0]["reviewStatus"]
        'draft'
    """
    out: list[dict[str, Any]] = []
    for row in rows:
        query = str(row.get("query") or row.get("q") or "").strip()
        if not query:
            continue
        label: dict[str, Any] = {
            "query": query,
            "targetKind": "",
            "expectedAnswerable": "",
            "expectedSourceRef": "",
            "goldOrigin": "userLog",
            "reviewStatus": "draft",
            "reviewerNote": "",
        }
        queryId = str(row.get("queryId") or row.get("id") or "").strip()
        if queryId:
            label["queryId"] = queryId
        candidateRefs = _candidateSourceRefs(row)
        if candidateRefs:
            label["candidateSourceRefs"] = candidateRefs
        topResults = row.get("topResults")
        if isinstance(topResults, list):
            label["topResults"] = topResults[:5]
        out.append(label)
    return out


def writeReviewerLabelTemplate(path: str | Path, rows: Iterable[Mapping[str, Any]]) -> None:
    """Write reviewer-label scaffold rows as JSONL.

    Args:
        path: Output JSONL path.
        rows: Raw query-log candidate rows.

    Returns:
        None.

    Raises:
        OSError: If the file cannot be written.

    Example:
        >>> callable(writeReviewerLabelTemplate)
        True
    """
    writeGoldLogRows(path, buildReviewerLabelTemplateRows(rows))


def loadGoldLogRows(paths: Iterable[str | Path]) -> list[dict[str, Any]]:
    """Load raw query-log or reviewer-label rows from JSON/JSONL files.

    Args:
        paths: Input file paths. Each file may be JSONL, JSON array, or a JSON object
            containing ``rows``, ``queries``, ``labels``, ``gold``, or ``queryLogGold``.

    Returns:
        list[dict[str, Any]]: Rows in file order.

    Raises:
        OSError: If a file cannot be read.
        ValueError: If a file shape is unsupported.

    Example:
        >>> callable(loadGoldLogRows)
        True
    """
    rows: list[dict[str, Any]] = []
    for path in paths:
        rows.extend(_loadRows(Path(path)))
    return rows


def mergeGoldLogRows(
    inputRows: Iterable[Mapping[str, Any]],
    labelRows: Iterable[Mapping[str, Any]] = (),
    *,
    defaultGoldOrigin: str = "",
    defaultReviewStatus: str = "",
) -> list[dict[str, Any]]:
    """Merge raw query rows and reviewer labels into canonical gold rows.

    Args:
        inputRows: Raw query-log or existing gold rows.
        labelRows: Reviewer label rows. Matching rows override input rows by
            ``queryId``/``id``/``query``; unmatched labels are appended.
        defaultGoldOrigin: Optional origin to fill when a label omitted it.
        defaultReviewStatus: Optional review status to fill when a label omitted it.

    Returns:
        list[dict[str, Any]]: Canonical rows suitable for ``evaluateSearchGold.py``.

    Raises:
        None.

    Example:
        >>> mergeGoldLogRows([{"query": "q", "target": "noAnswer"}])[0]["targetKind"]
        'noAnswer'
    """
    merged: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for raw in inputRows:
        row = dict(raw)
        key = _rowKey(row)
        if not key:
            key = f"row:{len(order)}"
        if key not in merged:
            order.append(key)
            merged[key] = row
        else:
            merged[key].update(row)

    for label in labelRows:
        key = _rowKey(label)
        if not key:
            key = f"label:{len(order)}"
        if key not in merged:
            order.append(key)
            merged[key] = {}
        merged[key].update(dict(label))

    return [
        normalizeGoldLogRow(
            merged[key],
            defaultGoldOrigin=defaultGoldOrigin,
            defaultReviewStatus=defaultReviewStatus,
        )
        for key in order
    ]


def normalizeGoldLogRow(
    row: Mapping[str, Any],
    *,
    defaultGoldOrigin: str = "",
    defaultReviewStatus: str = "",
) -> dict[str, Any]:
    """Normalize one query-log gold row.

    Args:
        row: Raw query-log or reviewer-label row.
        defaultGoldOrigin: Optional origin to fill if row omitted it.
        defaultReviewStatus: Optional review status to fill if row omitted it.

    Returns:
        dict[str, Any]: Canonical query-log gold row.

    Raises:
        None.

    Example:
        >>> normalizeGoldLogRow({"q": "없는 공시", "expectedAnswerable": False})["targetKind"]
        'noAnswer'
    """
    query = str(row.get("query") or row.get("q") or row.get("text") or "").strip()
    target = normalizeTargetKind(row)
    expectedAnswerable = _expectedAnswerable(row, target)
    if expectedAnswerable is False:
        target = "noAnswer"

    expectedRefs = _expectedSourceRefs(row)
    out: dict[str, Any] = {
        "query": query,
        "targetKind": target,
        "expectedAnswerable": expectedAnswerable,
        "goldOrigin": str(row.get("goldOrigin") or defaultGoldOrigin or "").strip(),
        "reviewStatus": str(row.get("reviewStatus") or defaultReviewStatus or "").strip(),
    }
    rowId = str(row.get("queryId") or row.get("id") or "").strip()
    if rowId:
        out["queryId"] = rowId
    if expectedRefs:
        out["expectedSourceRefs"] = expectedRefs
        out["expectedSourceRef"] = expectedRefs[0]

    for sourceKey, targetKey in (
        ("rceptNo", "rceptNo"),
        ("rcept_no", "rceptNo"),
        ("accession", "accession"),
        ("url", "url"),
        ("link", "url"),
        ("title", "title"),
        ("sourceDataAsOf", "sourceDataAsOf"),
        ("dataAsOf", "sourceDataAsOf"),
        ("reviewedAt", "reviewedAt"),
        ("labeler", "labeler"),
        ("note", "note"),
    ):
        value = row.get(sourceKey)
        if value not in (None, "") and targetKey not in out:
            out[targetKey] = value
    return out


def summarizeGoldLogRows(
    rows: Iterable[Mapping[str, Any]],
    *,
    minRows: int = 100,
    requiredTargets: Iterable[str] = DEFAULT_REQUIRED_TARGETS,
    requireRealReviewed: bool = True,
    requireSourceRef: bool = True,
) -> dict[str, Any]:
    """Summarize release-readiness of canonical query-log gold rows.

    Args:
        rows: Canonical query-log gold rows.
        minRows: Minimum row count for release graduation.
        requiredTargets: Target kinds required for coverage.
        requireRealReviewed: True requires real-origin and reviewed rows.
        requireSourceRef: True requires answerable rows to carry sourceRef gold.

    Returns:
        dict[str, Any]: Counts, invalid row reasons, blockers, and eligibility.

    Raises:
        None.

    Example:
        >>> summarizeGoldLogRows([], minRows=0)["releaseEligible"]
        False
    """
    normalizedRows = [dict(row) for row in rows]
    coverage: dict[str, int] = {}
    originCounts: dict[str, int] = {}
    reviewCounts: dict[str, int] = {}
    invalidRows: list[dict[str, Any]] = []

    for index, row in enumerate(normalizedRows):
        target = normalizeTargetKind(row)
        coverage[target] = coverage.get(target, 0) + 1
        origin = str(row.get("goldOrigin") or "")
        review = str(row.get("reviewStatus") or "")
        originCounts[origin] = originCounts.get(origin, 0) + 1
        reviewCounts[review] = reviewCounts.get(review, 0) + 1
        reasons = _invalidReasons(row, requireRealReviewed=requireRealReviewed, requireSourceRef=requireSourceRef)
        if reasons:
            invalidRows.append(
                {
                    "rowIndex": index,
                    "query": str(row.get("query") or ""),
                    "targetKind": target,
                    "reasons": reasons,
                }
            )

    realReviewedRows = sum(1 for row in normalizedRows if _isRealReviewed(row))
    blockers: list[str] = []
    if len(normalizedRows) < minRows:
        blockers.append(f"minRows:{len(normalizedRows)}/{minRows}")
    if requireRealReviewed and realReviewedRows < minRows:
        blockers.append(f"realReviewedRows:{realReviewedRows}/{minRows}")
    for target in requiredTargets:
        normalizedTarget = normalizeTargetKind({"target": target})
        if coverage.get(normalizedTarget, 0) == 0:
            blockers.append(f"missingTarget:{normalizedTarget}")
    if invalidRows:
        blockers.append(f"invalidRows:{len(invalidRows)}")

    return {
        "totalRows": len(normalizedRows),
        "realReviewedRows": realReviewedRows,
        "coverageByKind": coverage,
        "goldOriginCounts": originCounts,
        "reviewStatusCounts": reviewCounts,
        "invalidRows": invalidRows,
        "blockers": blockers,
        "releaseEligible": not blockers,
    }


def writeGoldLogRows(path: str | Path, rows: Iterable[Mapping[str, Any]]) -> None:
    """Write canonical query-log gold rows as JSONL.

    Args:
        path: Output JSONL path.
        rows: Canonical rows.

    Returns:
        None.

    Raises:
        OSError: If the file cannot be written.

    Example:
        >>> callable(writeGoldLogRows)
        True
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(dict(row), ensure_ascii=False, sort_keys=True) for row in rows]
    p.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def writeGoldSummary(path: str | Path, summary: Mapping[str, Any]) -> None:
    """Write query-log gold preparation summary as JSON.

    Args:
        path: Output JSON path.
        summary: Summary payload.

    Returns:
        None.

    Raises:
        OSError: If the file cannot be written.

    Example:
        >>> callable(writeGoldSummary)
        True
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(dict(summary), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _loadRows(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    data = json.loads(text) if text.strip() else []
    if isinstance(data, list):
        return [dict(row) for row in data if isinstance(row, Mapping)]
    if isinstance(data, dict):
        for key in ("rows", "queries", "labels", "gold", "queryLogGold"):
            rows = data.get(key)
            if isinstance(rows, list):
                return [dict(row) for row in rows if isinstance(row, Mapping)]
    raise ValueError(f"unsupported query-log shape: {path}")


def _rowKey(row: Mapping[str, Any]) -> str:
    return str(row.get("queryId") or row.get("id") or row.get("query") or row.get("q") or "").strip()


def _expectedAnswerable(row: Mapping[str, Any], target: str) -> bool:
    value = row.get("expectedAnswerable")
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"0", "false", "no", "n"}:
            return False
        if lowered in {"1", "true", "yes", "y"}:
            return True
    return target != "noAnswer"


def _expectedSourceRefs(row: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("expectedSourceRefs", "expectedSourceRef", "sourceRef"):
        value = row.get(key)
        if isinstance(value, str):
            values.extend(part.strip() for part in value.split(",") if part.strip())
        elif isinstance(value, Sequence):
            values.extend(str(item).strip() for item in value if str(item).strip())
    out: list[str] = []
    for value in values:
        if value not in out:
            out.append(value)
    return out


def _invalidReasons(
    row: Mapping[str, Any],
    *,
    requireRealReviewed: bool,
    requireSourceRef: bool,
) -> list[str]:
    reasons: list[str] = []
    query = str(row.get("query") or "").strip()
    target = normalizeTargetKind(row)
    expectedAnswerable = _expectedAnswerable(row, target)
    if not query:
        reasons.append("missingQuery")
    if not target:
        reasons.append("missingTargetKind")
    if target == "noAnswer" and expectedAnswerable is not False:
        reasons.append("noAnswerExpectedAnswerableTrue")
    if target != "noAnswer" and expectedAnswerable is False:
        reasons.append("answerableTargetExpectedFalse")
    if requireSourceRef and target != "noAnswer" and not _expectedSourceRefs(row):
        reasons.append("missingExpectedSourceRef")
    if requireRealReviewed and not _isRealOrigin(row):
        reasons.append("proxyGoldOrigin")
    if requireRealReviewed and not _isReviewed(row):
        reasons.append("unreviewedGold")
    return reasons


def _isRealReviewed(row: Mapping[str, Any]) -> bool:
    return _isRealOrigin(row) and _isReviewed(row)


def _isRealOrigin(row: Mapping[str, Any]) -> bool:
    return str(row.get("goldOrigin") or "") in REAL_GOLD_ORIGINS


def _isReviewed(row: Mapping[str, Any]) -> bool:
    return str(row.get("reviewStatus") or "") in REVIEWED_STATUSES


def _queryLogTopK(topK: int | None) -> int:
    if topK is not None:
        return max(1, int(topK))
    raw = os.environ.get(QUERY_LOG_TOPK_ENV, "").strip()
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            return 10
    return 10


def _queryEventId(query: str, params: Mapping[str, Any]) -> str:
    payload = json.dumps(
        {
            "query": str(query or ""),
            "params": {str(key): params.get(key) for key in sorted(params)},
            "timeBucket": time.strftime("%Y%m%dT%H%M%S"),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
    return f"search:{time.strftime('%Y%m%dT%H%M%S')}:{digest}"


def _projectResultRow(row: Mapping[str, Any]) -> dict[str, Any]:
    projected: dict[str, Any] = {}
    for sourceKey, targetKey in (
        ("source", "source"),
        ("sourceRef", "sourceRef"),
        ("rcept_no", "rceptNo"),
        ("corp_name", "companyName"),
        ("stock_code", "stockCode"),
        ("report_nm", "reportName"),
        ("section_title", "title"),
        ("dataAsOf", "dataAsOf"),
        ("answerable", "answerable"),
        ("notAnswerableReason", "notAnswerableReason"),
        ("scope", "scope"),
        ("dartUrl", "url"),
        ("url", "url"),
        ("score", "score"),
    ):
        value = row.get(sourceKey)
        if value not in (None, "") and targetKey not in projected:
            projected[targetKey] = _jsonScalar(value)
    return projected


def _jsonScalar(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    try:
        return value.item()
    except AttributeError:
        return str(value)


def _dataAsOfBySource(rows: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in rows:
        source = str(row.get("source") or "")
        dataAsOf = str(row.get("dataAsOf") or "")
        if source and dataAsOf and dataAsOf > out.get(source, ""):
            out[source] = dataAsOf
    return out


def _candidateSourceRefs(row: Mapping[str, Any]) -> list[str]:
    raw = row.get("topSourceRefs") or row.get("candidateSourceRefs") or []
    values: list[str] = []
    if isinstance(raw, str):
        values.extend(part.strip() for part in raw.split(",") if part.strip())
    elif isinstance(raw, Sequence):
        values.extend(str(item).strip() for item in raw if str(item).strip())
    topRef = str(row.get("topSourceRef") or "").strip()
    if topRef:
        values.insert(0, topRef)
    out: list[str] = []
    for value in values:
        if value not in out:
            out.append(value)
    return out

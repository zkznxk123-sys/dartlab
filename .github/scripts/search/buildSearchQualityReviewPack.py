"""Build a real-index search quality review pack.

This is not a release gate by itself. It runs or imports diverse search
queries, preserves top results, and writes reviewer-ready raw log / label
template artifacts so the next step can become real query-log gold.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

DEFAULT_QUERY_SPECS: tuple[dict[str, Any], ...] = (
    {"query": "유상증자 공시 원문", "targetKindHint": "filing", "scope": "auto"},
    {"query": "주주총회 소집 의안", "targetKindHint": "filing", "scope": "auto"},
    {"query": "단일판매 공급계약 체결", "targetKindHint": "filing", "scope": "auto"},
    {"query": "임직원 스톡옵션 부여", "targetKindHint": "filing", "scope": "auto"},
    {"query": "대량보유 지분 변동 보고", "targetKindHint": "filing", "scope": "auto"},
    {"query": "환율 리스크 사업보고서 본문", "targetKindHint": "filing", "scope": "content"},
    {"query": "반도체 HBM 투자 사업의 내용", "targetKindHint": "filing", "scope": "content"},
    {"query": "우발부채 소송 충당부채 주석", "targetKindHint": "filing", "scope": "content"},
    {"query": "공시 말고 뉴스로 반도체 투자", "targetKindHint": "news", "scope": "news"},
    {"query": "공시 말고 뉴스로 환율 기사", "targetKindHint": "news", "scope": "news"},
    {"query": "뉴스 기사 AI 반도체 수출", "targetKindHint": "news", "scope": "news"},
    {"query": "EDGAR 10-K risk factors", "targetKindHint": "edgar", "scope": "auto"},
    {"query": "EDGAR revenue recognition liquidity", "targetKindHint": "edgar", "scope": "auto"},
    {"query": "management discussion and analysis cash flow", "targetKindHint": "edgar", "scope": "auto"},
    {"query": "없는회사 2099년 합병 공시", "targetKindHint": "noAnswer", "scope": "auto"},
    {"query": "zzqwvxnotlistedalpha999", "targetKindHint": "noAnswer", "scope": "auto"},
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, help="Directory for review pack artifacts.")
    parser.add_argument("--query", action="append", default=[], help="Ad hoc query. May be repeated.")
    parser.add_argument("--query-spec", action="append", default=[], help="JSON/JSONL query spec path.")
    parser.add_argument("--results-json", help="Precomputed results by query JSON path.")
    parser.add_argument("--no-default-queries", action="store_true", help="Use only provided query/query-spec rows.")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--scope", default="auto", help="Fallback scope for --query rows.")
    parser.add_argument("--min-queries", type=int, default=12)
    parser.add_argument("--required-targets", default="filing,news,noAnswer,edgar")
    parser.add_argument("--fail-on-error", action="store_true")
    args = parser.parse_args(argv)

    specs = [] if args.no_default_queries else list(DEFAULT_QUERY_SPECS)
    for path in args.query_spec:
        specs.extend(loadQuerySpecs(path))
    specs.extend({"query": query, "targetKindHint": "", "scope": args.scope} for query in args.query)

    report = buildQualityReviewPack(
        outDir=Path(args.out_dir),
        querySpecs=specs,
        resultsByQuery=loadResultsByQuery(args.results_json) if args.results_json else None,
        limit=args.limit,
        minQueries=args.min_queries,
        requiredTargets=[part.strip() for part in args.required_targets.split(",") if part.strip()],
    )
    print(json.dumps({"valid": report["valid"], "blockers": report["blockers"]}, ensure_ascii=False))
    if args.fail_on_error and not report["valid"]:
        return 1
    return 0


def buildQualityReviewPack(
    *,
    outDir: Path,
    querySpecs: Iterable[Mapping[str, Any]],
    resultsByQuery: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    limit: int = 10,
    minQueries: int = 12,
    requiredTargets: Sequence[str] = ("filing", "news", "noAnswer", "edgar"),
) -> dict[str, Any]:
    """Run or import search results and write reviewer-ready quality artifacts."""
    from dartlab.providers.dart.search.goldLog import (
        buildRawQueryLogEvent,
        buildReviewerLabelTemplateRows,
        writeGoldLogRows,
    )

    outDir.mkdir(parents=True, exist_ok=True)
    specs = _dedupeSpecs(querySpecs)
    resultItems: list[dict[str, Any]] = []
    rawEvents: list[dict[str, Any]] = []
    latencyMs: list[float] = []
    precomputed = resultsByQuery is not None

    for spec in specs:
        query = str(spec.get("query") or "").strip()
        if not query:
            continue
        scope = str(spec.get("scope") or "auto")
        corp = _optionalText(spec.get("corp"))
        start = _optionalText(spec.get("start"))
        end = _optionalText(spec.get("end"))
        if resultsByQuery is None:
            started = time.perf_counter()
            rows = _runSearch(query=query, corp=corp, start=start, end=end, limit=limit, scope=scope)
            latencyMs.append((time.perf_counter() - started) * 1000.0)
        else:
            rows = [dict(row) for row in resultsByQuery.get(query, [])][:limit]
        item = {
            "query": query,
            "targetKindHint": str(spec.get("targetKindHint") or spec.get("target") or ""),
            "scope": scope,
            "corp": corp or "",
            "start": start or "",
            "end": end or "",
            "results": [_jsonDict(row) for row in rows],
        }
        resultItems.append(item)
        event = buildRawQueryLogEvent(
            query=query,
            params={
                "scope": scope,
                "corp": corp,
                "start": start,
                "end": end,
                "limit": limit,
                "targetKindHint": item["targetKindHint"],
            },
            results=rows,
            topK=limit,
        )
        event["targetKindHint"] = item["targetKindHint"]
        rawEvents.append(event)

    rawPath = outDir / "queryLogRaw.reviewPack.jsonl"
    labelPath = outDir / "queryLogLabels.todo.jsonl"
    resultsPath = outDir / "queryResults.json"
    reportPath = outDir / "qualityReviewPack.json"
    labelRows = _labelTemplateRows(rawEvents, buildReviewerLabelTemplateRows(rawEvents))
    writeGoldLogRows(rawPath, rawEvents)
    writeGoldLogRows(labelPath, labelRows)
    _writeJson(resultsPath, resultItems)

    report = _buildReport(
        resultItems=resultItems,
        rawPath=rawPath,
        labelPath=labelPath,
        resultsPath=resultsPath,
        reportPath=reportPath,
        labelRows=labelRows,
        latencyMs=latencyMs,
        precomputed=precomputed,
        minQueries=minQueries,
        requiredTargets=requiredTargets,
    )
    _writeJson(reportPath, report)
    return report


def loadQuerySpecs(path: str | Path) -> list[dict[str, Any]]:
    """Load query specs from JSON, JSONL, or plain-line files."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".jsonl":
        return [_querySpecFromLine(line) for line in text.splitlines() if line.strip()]
    if p.suffix.lower() == ".txt":
        return [{"query": line.strip()} for line in text.splitlines() if line.strip()]
    data = json.loads(text) if text.strip() else []
    if isinstance(data, list):
        return [_normalizeSpec(item) for item in data]
    if isinstance(data, dict):
        rows = data.get("queries") or data.get("rows") or data.get("querySpecs")
        if isinstance(rows, list):
            return [_normalizeSpec(item) for item in rows]
    raise ValueError(f"unsupported query spec shape: {p}")


def loadResultsByQuery(path: str | Path) -> dict[str, list[dict[str, Any]]]:
    """Load precomputed search results keyed by query."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return {str(query): [dict(row) for row in rows] for query, rows in data.items()}
    if isinstance(data, list):
        out: dict[str, list[dict[str, Any]]] = {}
        for item in data:
            if isinstance(item, dict):
                out[str(item.get("query") or "")] = [dict(row) for row in item.get("results", [])]
        return out
    raise ValueError(f"unsupported results-json shape: {path}")


def _runSearch(
    *,
    query: str,
    corp: str | None,
    start: str | None,
    end: str | None,
    limit: int,
    scope: str,
) -> list[dict[str, Any]]:
    import dartlab

    df = dartlab.search(query, corp=corp, start=start, end=end, limit=limit, scope=scope)
    return df.to_dicts()


def _buildReport(
    *,
    resultItems: Sequence[Mapping[str, Any]],
    rawPath: Path,
    labelPath: Path,
    resultsPath: Path,
    reportPath: Path,
    labelRows: Sequence[Mapping[str, Any]],
    latencyMs: Sequence[float],
    precomputed: bool,
    minQueries: int,
    requiredTargets: Sequence[str],
) -> dict[str, Any]:
    coverage: dict[str, int] = {}
    topSources: dict[str, int] = {}
    resultRows = 0
    answerableRows = 0
    noResultQueries: list[str] = []
    sourceHintMisses: list[dict[str, Any]] = []
    noAnswerFalseAccepts: list[str] = []

    for item in resultItems:
        target = str(item.get("targetKindHint") or "unknown")
        coverage[target] = coverage.get(target, 0) + 1
        rows = [dict(row) for row in item.get("results", []) if isinstance(row, Mapping)]
        resultRows += len(rows)
        if not rows and target != "noAnswer":
            noResultQueries.append(str(item.get("query") or ""))
        for row in rows:
            source = str(row.get("source") or "")
            if source:
                topSources[source] = topSources.get(source, 0) + 1
            if _isAnswerable(row):
                answerableRows += 1
        _collectIntentWarnings(item, rows, sourceHintMisses, noAnswerFalseAccepts)

    blockers: list[str] = []
    if len(resultItems) < minQueries:
        blockers.append(f"minQueries:{len(resultItems)}/{minQueries}")
    for target in requiredTargets:
        if coverage.get(target, 0) <= 0:
            blockers.append(f"missingTargetHint:{target}")
    if noResultQueries:
        blockers.append(f"noResultQueries:{len(noResultQueries)}")
    if sourceHintMisses:
        blockers.append(f"sourceHintMisses:{len(sourceHintMisses)}")
    if noAnswerFalseAccepts:
        blockers.append(f"noAnswerFalseAccepts:{len(noAnswerFalseAccepts)}")

    return {
        "valid": not blockers,
        "releaseEvidence": False,
        "blockers": blockers,
        "queryCount": len(resultItems),
        "totalResultRows": resultRows,
        "answerableRows": answerableRows,
        "answerableRate": _ratio(answerableRows, resultRows),
        "coverageByTargetHint": coverage,
        "topSourceCounts": topSources,
        "labelProposalCounts": _labelProposalCounts(labelRows),
        "precomputedResults": precomputed,
        "latencyMs": _latencySummary(latencyMs),
        "warmLatencyMs": _latencySummary(latencyMs[1:]) if len(latencyMs) > 1 else _latencySummary(()),
        "noResultQueries": noResultQueries,
        "sourceHintMisses": sourceHintMisses[:20],
        "noAnswerFalseAccepts": noAnswerFalseAccepts[:20],
        "paths": {
            "rawLog": str(rawPath),
            "labelTemplate": str(labelPath),
            "resultsJson": str(resultsPath),
            "report": str(reportPath),
        },
        "nextStep": (
            "Reviewer must inspect proposed* fields in queryLogLabels.todo.jsonl, copy only verified "
            "values into targetKind/expectedSourceRef(s) or expectedAnswerable=false, and mark "
            "reviewStatus=reviewed before prepareSearchGold.py can produce release gold."
        ),
    }


def _collectIntentWarnings(
    item: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    sourceHintMisses: list[dict[str, Any]],
    noAnswerFalseAccepts: list[str],
) -> None:
    target = str(item.get("targetKindHint") or "")
    query = str(item.get("query") or "")
    if target == "noAnswer":
        if any(_isAnswerable(row) for row in rows[:10]):
            noAnswerFalseAccepts.append(query)
        return
    expectedSource = {"news": "news", "edgar": "edgar-panel"}.get(target)
    if expectedSource and any(str(row.get("source") or "") != expectedSource for row in rows[:10]):
        sourceHintMisses.append(
            {
                "query": query,
                "targetKindHint": target,
                "expectedSource": expectedSource,
                "topSources": [str(row.get("source") or "") for row in rows[:10]],
            }
        )


def _labelTemplateRows(
    rawRows: Sequence[Mapping[str, Any]], templateRows: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    byQuery = {str(row.get("query") or ""): dict(row) for row in rawRows}
    out: list[dict[str, Any]] = []
    for row in templateRows:
        item = dict(row)
        raw = byQuery.get(str(item.get("query") or ""), {})
        hint = str(raw.get("targetKindHint") or "")
        if hint:
            item["targetKindHint"] = hint
        item.update(_labelProposal(raw, hint))
        item["reviewStatus"] = "draft"
        item["reviewInstruction"] = (
            "Do not use this row as release gold until a reviewer fills targetKind and "
            "expectedSourceRef/expectedSourceRefs or expectedAnswerable=false, then sets reviewStatus=reviewed. "
            "proposed* fields are review accelerators only and are not release labels."
        )
        out.append(item)
    return out


def _labelProposal(raw: Mapping[str, Any], hint: str) -> dict[str, Any]:
    topResults = raw.get("topResults")
    rows = [dict(row) for row in topResults if isinstance(row, Mapping)] if isinstance(topResults, list) else []
    answerableRows = [row for row in rows if _isAnswerable(row)]
    proposal: dict[str, Any] = {}
    if hint:
        proposal["proposedTargetKind"] = hint

    if hint == "noAnswer":
        if answerableRows:
            proposal["proposedLabelReason"] = "noAnswerHintHasAnswerableTopResults"
            proposal["proposedReviewAction"] = "inspectPossibleFalseAcceptBeforeLabeling"
            return proposal
        proposal["proposedExpectedAnswerable"] = False
        proposal["proposedLabelReason"] = "noAnswerHintNoAnswerableTopResults"
        proposal["proposedReviewAction"] = "verifyNoAnswerThenSetExpectedAnswerableFalse"
        return proposal

    expectedSources = _expectedSources(hint)
    if expectedSources:
        matchingRows = [row for row in answerableRows if str(row.get("source") or "") in expectedSources]
        if not matchingRows:
            proposal["proposedLabelReason"] = "sourceHintMismatchNoProposal"
            proposal["proposedReviewAction"] = "inspectSourceIntentBeforeLabeling"
            return proposal
        answerableRows = matchingRows

    sourceRefs = _uniqueSourceRefs(answerableRows)
    if sourceRefs:
        proposal["proposedExpectedAnswerable"] = True
        proposal["proposedExpectedSourceRef"] = sourceRefs[0]
        proposal["proposedExpectedSourceRefs"] = sourceRefs[:3]
        proposal["proposedLabelReason"] = "topAnswerableResult"
        proposal["proposedReviewAction"] = "verifyProposalThenCopyToExpectedFields"
        source = str(answerableRows[0].get("source") or "")
        if source:
            proposal["proposedSource"] = source
        return proposal

    if rows:
        proposal["proposedLabelReason"] = "topResultsNotAnswerable"
        proposal["proposedReviewAction"] = "inspectFacetMismatchBeforeLabeling"
    else:
        proposal["proposedLabelReason"] = "noTopResults"
        proposal["proposedReviewAction"] = "inspectNoResultBeforeLabeling"
    return proposal


def _expectedSources(hint: str) -> set[str]:
    if hint == "news":
        return {"news"}
    if hint == "edgar":
        return {"edgar-panel"}
    if hint == "filing":
        return {"allFilings", "panel"}
    return set()


def _labelProposalCounts(labelRows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "total": len(labelRows),
        "withProposedSourceRef": sum(1 for row in labelRows if row.get("proposedExpectedSourceRef")),
        "withProposedNoAnswer": sum(1 for row in labelRows if row.get("proposedExpectedAnswerable") is False),
        "needsInspection": sum(
            1 for row in labelRows if str(row.get("proposedReviewAction") or "").startswith("inspect")
        ),
    }


def _uniqueSourceRefs(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    refs: list[str] = []
    for row in rows:
        sourceRef = str(row.get("sourceRef") or "").strip()
        if sourceRef and sourceRef not in refs:
            refs.append(sourceRef)
    return refs


def _querySpecFromLine(line: str) -> dict[str, Any]:
    text = line.strip()
    if text.startswith("{"):
        return _normalizeSpec(json.loads(text))
    return {"query": text}


def _normalizeSpec(item: Any) -> dict[str, Any]:
    if isinstance(item, str):
        return {"query": item}
    if isinstance(item, Mapping):
        return dict(item)
    raise ValueError(f"unsupported query spec item: {item!r}")


def _dedupeSpecs(querySpecs: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for spec in querySpecs:
        item = dict(spec)
        query = str(item.get("query") or item.get("q") or "").strip()
        if not query or query in seen:
            continue
        item["query"] = query
        seen.add(query)
        out.append(item)
    return out


def _latencySummary(values: Sequence[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "p50": None, "p95": None, "max": None}
    ordered = sorted(float(value) for value in values)
    return {
        "count": len(ordered),
        "p50": statistics.median(ordered),
        "p95": ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))],
        "max": max(ordered),
    }


def _isAnswerable(row: Mapping[str, Any]) -> bool:
    value = row.get("answerable")
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return True
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "no", "n"}
    return bool(value)


def _jsonDict(row: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): _jsonValue(value) for key, value in row.items()}


def _jsonValue(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Mapping):
        return {str(k): _jsonValue(v) for k, v in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_jsonValue(item) for item in value]
    try:
        return value.item()
    except AttributeError:
        return str(value)


def _optionalText(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator)


def _writeJson(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())

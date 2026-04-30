"""Request-local analysis workspace for AI result bundles.

The workspace is not a planner. It records artifacts produced during one
request so the runtime can expose evidence, claims, visuals, and limits in a
machine-readable shape.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from typing import Any

from dartlab.ai.runtime.contract_graph import (
    contractForTool,
    requiresVisualExplanation,
    routeQuestion,
    understandingPacketForQuestion,
)


@dataclass
class EvidenceItem:
    id: str
    sourceTool: str
    target: str | None = None
    metric: str | None = None
    period: str | None = None
    asOf: str | None = None
    value: Any | None = None
    unit: str | None = None
    basis: str | None = None
    artifactIds: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def toDict(self) -> dict[str, Any]:
        return _drop_empty(_json_safe(asdict(self)))


@dataclass
class ClaimItem:
    id: str
    text: str
    kind: str = "statement"
    targets: list[str] = field(default_factory=list)
    evidenceIds: list[str] = field(default_factory=list)
    confidence: str = "medium"
    status: str = "unverified"

    def toDict(self) -> dict[str, Any]:
        return _drop_empty(_json_safe(asdict(self)))


@dataclass
class VisualItem:
    id: str
    vizType: str
    purpose: str
    spec: dict[str, Any]
    evidenceIds: list[str] = field(default_factory=list)
    primary: bool = False

    def toDict(self) -> dict[str, Any]:
        return _drop_empty(_json_safe(asdict(self)))


class AnalysisWorkspace:
    """Accumulates one request's evidence, claims, visuals, and limits."""

    def __init__(self, *, question: str | None = None):
        self.question = question or ""
        self.route: dict[str, Any] = routeQuestion(self.question)
        self.understandingPacket: dict[str, Any] = understandingPacketForQuestion(self.question)
        self.evidence: list[EvidenceItem] = []
        self.claims: list[ClaimItem] = []
        self.visuals: list[VisualItem] = []
        self.limits: list[str] = []
        self.coverage: dict[str, Any] = {
            "routeIds": list(self.route.get("routeIds") or []),
            "contractIds": list(self.route.get("contractIds") or []),
            "processMapIds": list(self.route.get("processMapIds") or []),
            "graph": dict(self.route.get("graph") or {}),
        }
        self.freshness: dict[str, Any] = {}
        self.latency: dict[str, Any] = {
            "llmRoundMs": [],
            "toolTotalMs": 0,
            "toolCalls": [],
            "rewriteCount": 0,
            "maxRoundsReached": False,
        }
        self.trace: dict[str, Any] = {
            "selectedTools": [],
            "skippedCandidateTools": [],
            "toolArgs": [],
            "sanitizedArgs": [],
            "evidenceIds": [],
            "claimIds": [],
            "visualIds": [],
        }
        self.visualRequirement: dict[str, Any] = {"required": False, "satisfied": False}
        self._seq = 0
        self._claimRecorded = False

    def recordToolCall(
        self,
        *,
        name: str,
        arguments: dict[str, Any] | None = None,
        sanitizedArguments: dict[str, Any] | None = None,
        round: int | None = None,
    ) -> None:
        """Record the selected tool and argument trace for audit summaries."""
        if name and name not in self.trace["selectedTools"]:
            self.trace["selectedTools"].append(name)
        row = _drop_empty(
            {
                "name": name,
                "args": _compact_args(arguments or {}),
                "round": round,
            }
        )
        if row:
            self.trace["toolArgs"].append(row)
        if sanitizedArguments is not None and sanitizedArguments != (arguments or {}):
            self.trace["sanitizedArgs"].append(
                _drop_empty(
                    {
                        "name": name,
                        "before": _compact_args(arguments or {}),
                        "after": _compact_args(sanitizedArguments),
                        "round": round,
                    }
                )
            )

    def finalizeTrace(self) -> None:
        """Fill trace fields derived from candidate tools and ledgers."""
        candidates = [str(v) for v in self.understandingPacket.get("candidateTools") or []]
        selected = set(str(v) for v in self.trace.get("selectedTools") or [])
        self.trace["skippedCandidateTools"] = [name for name in candidates if name not in selected][:20]
        self.trace["evidenceIds"] = [item.id for item in self.evidence[:50]]
        self.trace["claimIds"] = [item.id for item in self.claims[:30]]
        self.trace["visualIds"] = [item.id for item in self.visuals[:20]]

    def recordToolResult(
        self,
        *,
        sourceTool: str,
        arguments: dict[str, Any] | None,
        result: Any,
        artifacts: list[dict[str, Any]] | None = None,
    ) -> list[EvidenceItem]:
        """Extract compact evidence candidates from a tool result."""
        artifactIds = [str(a.get("id") or a.get("url")) for a in artifacts or [] if isinstance(a, dict)]
        args = arguments or {}
        contract = contractForTool(sourceTool, args)
        evidenceSchema = contract.evidenceSchema if contract is not None else {}
        before = len(self.evidence)

        if result is None:
            self.addLimit(f"{sourceTool}: result is None")
            return []
        if sourceTool in {"disclosure", "filings", "liveFilings"}:
            self.addLimit("disclosure: basis=title_list; filing body not read")

        for row in _rows_from_result(result):
            item = self._evidenceFromRow(sourceTool, args, row, artifactIds, evidenceSchema=evidenceSchema)
            if item is not None:
                self.evidence.append(item)
                self.trace["evidenceIds"].append(item.id)
                self._observeEvidence(args, item)
                if len(self.evidence) - before >= 30:
                    self.addLimit(f"{sourceTool}: evidence truncated to 30 rows")
                    break

        if len(self.evidence) == before:
            summary = _summary_from_result(result)
            if summary:
                item = EvidenceItem(
                    id=self._next_id("ev"),
                    sourceTool=sourceTool,
                    target=_target_from_args(args),
                    metric=_metric_from_args(args),
                    basis=summary,
                    artifactIds=artifactIds,
                )
                self.evidence.append(item)
                self.trace["evidenceIds"].append(item.id)
                self._observeEvidence(args, item)

        return self.evidence[before:]

    def recordVisualSpec(
        self,
        spec: dict[str, Any],
        *,
        purpose: str = "explain",
        evidenceIds: list[str] | None = None,
    ) -> VisualItem:
        normalized = _normalize_visual_spec(spec)
        vizType = str(normalized.get("vizType") or ("diagram" if normalized.get("diagramType") else "chart"))
        linked = list(evidenceIds or [e.id for e in self.evidence[-30:]])
        item = VisualItem(
            id=self._next_id("viz"),
            vizType=vizType,
            purpose=purpose,
            spec=_json_safe(normalized),
            evidenceIds=linked,
            primary=not self.visuals,
        )
        self.visuals.append(item)
        self.trace["visualIds"].append(item.id)
        return item

    def recordFinalAnswer(self, answer: str) -> list[ClaimItem]:
        """Create a compact claim ledger from the final answer text."""
        if self._claimRecorded:
            return []
        self._claimRecorded = True
        before = len(self.claims)
        evidenceIds = [e.id for e in self.evidence[:30]]
        targets = sorted({e.target for e in self.evidence if e.target})
        for text in _claim_sentences(answer):
            kind = "judgment" if _looks_like_judgment(text) else "statement"
            self.claims.append(
                ClaimItem(
                    id=self._next_id("claim"),
                    text=text,
                    kind=kind,
                    targets=targets[:8],
                    evidenceIds=evidenceIds,
                    confidence="medium" if evidenceIds else "low",
                    status="supported" if evidenceIds else "unverified",
                )
            )
            self.trace["claimIds"].append(self.claims[-1].id)
            if len(self.claims) - before >= 12:
                self.addLimit("claims truncated to 12 items")
                break
        return self.claims[before:]

    def ensureRequiredVisuals(self, *, answer: str | None = None) -> list[VisualItem]:
        """Compile a request-level visual explanation when the question requires one."""
        required, reason = _visual_requirement(self.question)
        self.visualRequirement = {
            "required": required,
            "reason": reason,
            "satisfied": bool(self.visuals),
        }
        if not required or self.visuals or not self.evidence:
            return []

        spec = _comparison_chart_spec(self.evidence) or _diagram_spec(self.evidence, answer or self.question)
        if not spec:
            return []
        evidenceIds = [item.id for item in self.evidence[:30]]
        visual = self.recordVisualSpec(spec, purpose=reason or "explain", evidenceIds=evidenceIds)
        self.visualRequirement["satisfied"] = True
        self.visualRequirement["generated"] = "workspace"
        return [visual]

    def compileComparisonBrief(self) -> str:
        """Return a compact same-axis evidence brief for comparison questions."""
        if "comparison.same_axis" not in set(self.coverage.get("contractIds") or []):
            required, reason = _visual_requirement(self.question)
            if not required or reason not in {"company_compare", "comparison"}:
                return ""
        targets = sorted({str(item.target) for item in self.evidence if item.target})
        if len(targets) < 2:
            return ""

        matrix: dict[str, dict[str, EvidenceItem]] = {}
        for item in self.evidence:
            if not item.target or not item.metric:
                continue
            if _numeric_value(item.value) is None and not item.basis:
                continue
            metric = str(item.metric)
            target = str(item.target)
            matrix.setdefault(metric, {})
            matrix[metric].setdefault(target, item)

        sameAxis = [(metric, values) for metric, values in matrix.items() if len(values) >= 2]
        partial = [(metric, values) for metric, values in matrix.items() if len(values) == 1]
        rows = sameAxis[:8] + partial[: max(0, 8 - len(sameAxis))]
        if not rows:
            return ""

        lines = [
            "[workspace comparison evidence]",
            "아래 표는 runtime Workspace가 tool_result evidence를 같은 축으로 압축한 것입니다. 답변에서는 '사용자 제공 근거'가 아니라 'tool 근거' 또는 'Workspace 근거'라고 표현하세요.",
            "",
            "| metric | " + " | ".join(targets[:4]) + " |",
            "| --- | " + " | ".join("---:" for _ in targets[:4]) + " |",
        ]
        for metric, values in rows:
            cells = []
            for target in targets[:4]:
                item = values.get(target)
                if item is None:
                    cells.append("데이터 미제공")
                    continue
                cells.append(_format_brief_value(item.value, item.unit, item.basis))
            lines.append("| " + " | ".join([metric, *cells]) + " |")
        lines.extend(
            [
                "",
                "사용 원칙: 같은 metric이 양쪽에 있을 때만 강한 비교 결론을 내리고, 한쪽만 있는 축은 한계로 표시하세요.",
            ]
        )
        return "\n".join(lines)

    def recordLlmRound(self, durationMs: int) -> None:
        self.latency.setdefault("llmRoundMs", []).append(max(0, int(durationMs)))

    def recordToolLatency(
        self,
        *,
        name: str,
        durationMs: int,
        resultSizeBytes: int | None = None,
        round: int | None = None,
    ) -> None:
        duration = max(0, int(durationMs))
        self.latency["toolTotalMs"] = int(self.latency.get("toolTotalMs") or 0) + duration
        self.latency.setdefault("toolCalls", []).append(
            _drop_empty(
                {
                    "name": name,
                    "durationMs": duration,
                    "resultSizeBytes": resultSizeBytes,
                    "round": round,
                }
            )
        )

    def noteQualityRewrite(self) -> None:
        self.latency["rewriteCount"] = int(self.latency.get("rewriteCount") or 0) + 1

    def markMaxRoundsReached(self) -> None:
        self.latency["maxRoundsReached"] = True

    def latencySummary(self) -> dict[str, Any]:
        llmRounds = [int(v) for v in self.latency.get("llmRoundMs") or []]
        toolCalls = [v for v in self.latency.get("toolCalls") or [] if isinstance(v, dict)]
        slowReasons: list[str] = []
        if len(llmRounds) + len(toolCalls) >= 8:
            slowReasons.append("too_many_rounds")
        if any(int(t.get("resultSizeBytes") or 0) > 50_000 for t in toolCalls):
            slowReasons.append("large_tool_result")
        if int(self.latency.get("rewriteCount") or 0) > 0:
            slowReasons.append("quality_rewrite")
        if any(t.get("name") == "story" and int(t.get("durationMs") or 0) > 60_000 for t in toolCalls):
            slowReasons.append("story_tool_slow")
        return {
            "llmRoundMs": sum(llmRounds),
            "toolTotalMs": int(self.latency.get("toolTotalMs") or 0),
            "rewriteCount": int(self.latency.get("rewriteCount") or 0),
            "maxRoundsReached": bool(self.latency.get("maxRoundsReached")),
            "slowReason": slowReasons,
        }

    def addLimit(self, message: str) -> None:
        if message and message not in self.limits:
            self.limits.append(message)

    def resultBundle(self) -> dict[str, Any]:
        self.finalizeTrace()
        return {
            "evidence": [e.toDict() for e in self.evidence],
            "claims": [c.toDict() for c in self.claims],
            "visuals": [v.toDict() for v in self.visuals],
            "limits": list(self.limits),
        }

    def summary(self) -> dict[str, Any]:
        self.finalizeTrace()
        quality = self.qualitySummary()
        return {
            "evidenceCount": len(self.evidence),
            "claimCount": len(self.claims),
            "visualCount": len(self.visuals),
            "limitCount": len(self.limits),
            "coverage": _drop_empty(_json_safe(self.coverage)),
            "graph": _drop_empty(_json_safe(self.graphSummary())),
            "trace": _drop_empty(_json_safe(self.traceSummary())),
            "quality": _drop_empty(_json_safe(quality)),
            "processMapSatisfied": bool(quality.get("processMapSatisfied")),
            "claimSupportRate": quality.get("claimSupportRate"),
            "toolArgValidRate": quality.get("toolArgValidRate"),
            "freshnessSatisfied": quality.get("freshnessSatisfied"),
            "visualSatisfied": quality.get("visualSatisfied"),
            "freshness": _drop_empty(_json_safe(self.freshness)),
            "visualRequirement": _drop_empty(_json_safe(self.visualRequirement)),
            **self.latencySummary(),
        }

    def traceSummary(self) -> dict[str, Any]:
        tool_args = [v for v in self.trace.get("toolArgs") or [] if isinstance(v, dict)]
        sanitized = [v for v in self.trace.get("sanitizedArgs") or [] if isinstance(v, dict)]
        return {
            "selectedTools": list(self.trace.get("selectedTools") or []),
            "skippedCandidateTools": list(self.trace.get("skippedCandidateTools") or []),
            "toolArgs": tool_args[:30],
            "sanitizedArgs": sanitized[:20],
            "toolArgValidRate": _ratio(max(0, len(tool_args) - len(sanitized)), len(tool_args)),
            "evidenceIds": list(dict.fromkeys(self.trace.get("evidenceIds") or []))[:50],
            "claimIds": list(dict.fromkeys(self.trace.get("claimIds") or []))[:30],
            "visualIds": list(dict.fromkeys(self.trace.get("visualIds") or []))[:20],
        }

    def qualitySummary(self) -> dict[str, Any]:
        graph = self.graphSummary()
        claims = [c for c in self.claims if c.kind == "judgment"] or list(self.claims)
        supported = [c for c in claims if c.status == "supported" and c.evidenceIds]
        stale = any(isinstance(v, dict) and v.get("staleDaily") for v in self.freshness.values())
        trace = self.traceSummary()
        return {
            "processMapSatisfied": bool(
                graph.get("requiredEvidenceSatisfied")
                and graph.get("artifactSatisfied")
                and graph.get("visualSatisfied")
            ),
            "claimSupportRate": _ratio(len(supported), len(claims)),
            "requiredEvidenceCoverage": graph.get("requiredEvidenceCoverage"),
            "freshnessSatisfied": not stale,
            "visualSatisfied": bool(graph.get("visualSatisfied")),
            "visualCoverage": 1.0 if graph.get("visualSatisfied") else 0.0,
            "toolArgValidRate": trace.get("toolArgValidRate"),
        }

    def graphSummary(self) -> dict[str, Any]:
        """Return contract/process satisfaction summary for audit and API metadata."""
        packet = self.understandingPacket
        required = [str(v) for v in packet.get("requiredEvidence") or []]
        observed = self._observedEvidenceKeys()
        artifact_required = _artifact_required(packet)
        visual_required = bool(packet.get("visualPolicy", {}).get("requiredFor"))
        artifact_satisfied = not artifact_required or any(item.artifactIds for item in self.evidence)
        visual_satisfied = not visual_required or bool(self.visuals)
        evidence_coverage = _required_evidence_coverage(required, observed, self)
        process_satisfied = bool(evidence_coverage >= 1 and artifact_satisfied and visual_satisfied)
        return {
            "routeHit": bool(self.coverage.get("routeIds")),
            "contractHit": bool(self.coverage.get("contractIds")),
            "processMapUsed": bool(self.coverage.get("processMapIds")),
            "routeIds": list(self.coverage.get("routeIds") or []),
            "contractIds": list(self.coverage.get("contractIds") or []),
            "processMapIds": list(self.coverage.get("processMapIds") or []),
            "requiredEvidence": required,
            "observedEvidence": sorted(observed),
            "requiredEvidenceSatisfied": evidence_coverage >= 1,
            "requiredEvidenceCoverage": evidence_coverage,
            "artifactRequired": artifact_required,
            "artifactSatisfied": artifact_satisfied,
            "visualRequired": visual_required,
            "visualSatisfied": visual_satisfied,
            "processMapSatisfied": process_satisfied,
            "acceptanceCriteria": _merge_process_values(packet.get("processMaps") or [], "acceptanceCriteria"),
        }

    def _observedEvidenceKeys(self) -> set[str]:
        observed: set[str] = set()
        if self.evidence:
            observed.add("evidence")
        for item in self.evidence:
            if item.target:
                observed.add("target")
            if item.metric:
                observed.add("metric")
            if item.period:
                observed.add("period")
            if item.asOf:
                observed.add("asOf")
            if item.value not in (None, ""):
                observed.add("value")
            if item.basis:
                observed.add("basis")
            if item.artifactIds:
                observed.add("artifact")
            if item.sourceTool == "industry":
                observed.add("industry")
                observed.add("universe")
            if item.sourceTool in {"disclosure", "filings", "liveFilings", "search"}:
                if item.period or item.asOf:
                    observed.add("filedAt")
                if item.basis or item.metric:
                    observed.add("title")
                if item.metric:
                    observed.add("formType")
            if item.sourceTool == "pythonExec" and len(self.evidence) >= 10:
                observed.add("universe")
        if len(self.evidence) >= 10:
            observed.add("universe")
        return observed

    def _next_id(self, prefix: str) -> str:
        self._seq += 1
        return f"{prefix}_{self._seq:04d}"

    def _evidenceFromRow(
        self,
        sourceTool: str,
        args: dict[str, Any],
        row: dict[str, Any],
        artifactIds: list[str],
        *,
        evidenceSchema: dict[str, Any] | None = None,
    ) -> EvidenceItem | None:
        schema = evidenceSchema or {}
        metric = _first_schema_key(row, schema.get("metricKeys")) or _metric_from_row(row) or _metric_from_args(args)
        value_key = _first_schema_key(row, schema.get("valueKeys"))
        value = row.get(value_key) if value_key else row.get(metric) if metric and metric in row else None
        unit = schema.get("unit") or _unit_from_metric(str(metric) if metric else "")
        basis = _schema_basis(row, schema.get("basisKeys")) or _basis_from_row(row)
        return EvidenceItem(
            id=self._next_id("ev"),
            sourceTool=sourceTool,
            target=_first_schema_value(row, schema.get("targetKeys"))
            or _target_from_row(row)
            or _target_from_args(args),
            metric=str(metric) if metric else None,
            period=_first_schema_value(row, schema.get("periodKeys")) or _period_from_row(row),
            asOf=_first_schema_value(row, schema.get("asOfKeys")) or _asof_from_row(row),
            value=_json_safe(value),
            unit=str(unit) if unit else None,
            basis=basis,
            artifactIds=artifactIds,
        )

    def _observeEvidence(self, args: dict[str, Any], item: EvidenceItem) -> None:
        target = item.target or _target_from_args(args)
        metric = item.metric or _metric_from_args(args)
        if target and metric:
            matrix = self.coverage.setdefault("matrix", {})
            matrix.setdefault(str(target), {})
            matrix[str(target)][str(metric)] = matrix[str(target)].get(str(metric), 0) + 1

        asOf = _parse_date(item.asOf or item.period)
        if asOf is None:
            return
        metricKey = ":".join(str(v) for v in (target, metric) if v) or item.sourceTool
        current = self.freshness.get(metricKey)
        if current and str(asOf) < str(current.get("latestAsOf", "")):
            return
        if not current or str(asOf) > str(current.get("latestAsOf", "")):
            self.freshness[metricKey] = {
                "latestAsOf": asOf.isoformat(),
                "target": target,
                "metric": metric,
                "cadence": _cadence(args, item),
            }
        if _is_stale_daily(args, item, asOf):
            self.addLimit(f"freshness: {metricKey} available through {asOf.isoformat()}")
            self.freshness[metricKey]["staleDaily"] = True


def _rows_from_result(result: Any) -> list[dict[str, Any]]:
    try:
        import polars as pl

        if isinstance(result, pl.DataFrame):
            frame = result.tail(30).reverse() if _has_time_axis(result.columns) else result.head(30)
            return [_json_safe(r) for r in frame.to_dicts()]
    except ImportError:
        pass

    if _is_tabular_list(result):
        return [_json_safe(r) for r in result[:30]]

    if isinstance(result, dict):
        rows: list[dict[str, Any]] = []
        for key, value in result.items():
            if key.startswith("_"):
                continue
            if _is_tabular_list(value):
                rows.extend(_json_safe(r) for r in value[:30])
            elif isinstance(value, dict):
                flat = {"block": key, **value}
                rows.append(_json_safe(flat))
        return rows[:30]

    if isinstance(result, str):
        return _parse_delimited_rows(result)[:30]

    return []


def _is_tabular_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(row, dict) for row in value)


def _parse_delimited_rows(text: str) -> list[dict[str, str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for delimiter in ("\t", ","):
        for idx, line in enumerate(lines):
            if delimiter not in line:
                continue
            headers = [cell.strip() for cell in line.split(delimiter)]
            if len(headers) < 2 or len(set(headers)) != len(headers):
                continue
            metadata = _parse_result_metadata(lines[:idx])
            rows: list[dict[str, str]] = []
            for body in lines[idx + 1 :]:
                if delimiter not in body:
                    if rows:
                        break
                    continue
                cells = [cell.strip() for cell in body.split(delimiter)]
                if len(cells) != len(headers):
                    if rows:
                        break
                    continue
                rows.append({**metadata, **dict(zip(headers, cells, strict=True))})
            if rows:
                return rows
    return []


def _has_time_axis(columns: Any) -> bool:
    for column in columns or []:
        if str(column).lower() in {"date", "asof", "as_of", "enddate", "latestdate", "period"}:
            return True
    return False


def _parse_result_metadata(lines: list[str]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in lines:
        if line.lower().startswith("period:"):
            payload = line.split(":", 1)[1].strip()
            parts = [part.strip() for part in payload.split(",") if part.strip()]
            if parts:
                metadata["period"] = parts[0]
                if "~" in parts[0]:
                    metadata["asOf"] = parts[0].split("~")[-1].strip()
            for part in parts[1:]:
                if "=" not in part:
                    continue
                key, value = [piece.strip() for piece in part.split("=", 1)]
                if key == "universe":
                    metadata["universe"] = value
                elif key == "metric":
                    metadata.setdefault("metric", value)
    return metadata


def _summary_from_result(result: Any) -> str | None:
    if isinstance(result, dict):
        summary = result.get("_summary")
        if isinstance(summary, str) and summary.strip():
            return summary.strip()[:500]
    if isinstance(result, str):
        first = next((line.strip() for line in result.splitlines() if line.strip()), "")
        return first[:500] if first else None
    return None


def _target_from_args(args: dict[str, Any]) -> str | None:
    for key in ("stockCode", "target", "keyword", "axis"):
        value = args.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def _metric_from_args(args: dict[str, Any]) -> str | None:
    for key in ("metric", "target", "axis", "topic"):
        value = args.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def _target_from_row(row: dict[str, Any]) -> str | None:
    for key in ("stockCode", "corpName", "company", "name", "target", "ticker", "symbol"):
        value = row.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def _metric_from_row(row: dict[str, Any]) -> str | None:
    preferred = (
        "returnPct",
        "changePct",
        "value",
        "close",
        "revenue",
        "operatingIncome",
        "roe",
        "opm",
        "score",
    )
    for key in preferred:
        if key in row and _is_number_like(row.get(key)):
            return key
    for key, value in row.items():
        if key.lower() in {"rank", "stockcode"}:
            continue
        if _is_number_like(value):
            return str(key)
    return None


def _schema_keys(keys: Any) -> tuple[str, ...]:
    if isinstance(keys, str):
        return (keys,)
    if isinstance(keys, (list, tuple)):
        return tuple(str(key) for key in keys)
    return ()


def _first_schema_key(row: dict[str, Any], keys: Any) -> str | None:
    for key in _schema_keys(keys):
        if key in row and row.get(key) not in (None, ""):
            return key
    return None


def _first_schema_value(row: dict[str, Any], keys: Any) -> str | None:
    key = _first_schema_key(row, keys)
    if key is None:
        return None
    value = row.get(key)
    return str(value) if value not in (None, "") else None


def _period_from_row(row: dict[str, Any]) -> str | None:
    for key in ("period", "year", "quarter", "date", "start", "end"):
        value = row.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def _asof_from_row(row: dict[str, Any]) -> str | None:
    for key in ("asOf", "asof", "date", "endDate", "latestDate"):
        value = row.get(key)
        if value not in (None, ""):
            return str(value)
    date_keys = sorted(k for k in row if re.fullmatch(r"20\d{2}-\d{2}-\d{2}", str(k)))
    return date_keys[-1] if date_keys else None


def _basis_from_row(row: dict[str, Any]) -> str | None:
    parts = []
    for key in ("rank", "stockCode", "corpName", "period", "asOf"):
        if row.get(key) not in (None, ""):
            parts.append(f"{key}={row[key]}")
    return ", ".join(parts)[:500] if parts else None


def _schema_basis(row: dict[str, Any], keys: Any) -> str | None:
    parts = []
    for key in _schema_keys(keys):
        if row.get(key) not in (None, ""):
            parts.append(f"{key}={row[key]}")
    return ", ".join(parts)[:500] if parts else None


def _unit_from_metric(metric: str) -> str | None:
    low = metric.lower()
    if "pct" in low or "%" in metric or "rate" in low or "margin" in low:
        return "%"
    if "price" in low or "close" in low:
        return "price"
    return None


def _visual_requirement(question: str) -> tuple[bool, str | None]:
    if requiresVisualExplanation(question):
        route = routeQuestion(question)
        profile = route.get("profileTypes") or []
        return True, str(profile[0]) if profile else "graph_contract"
    q = question.lower()
    if any(word in q for word in ("비교", "compare", "vs", "경쟁력")):
        return True, "comparison"
    if any(word in q for word in ("추이", "시계열", "기간", "상승", "오른", "랭킹", "순위", "return", "trend", "rank")):
        return True, "trend_or_ranking"
    if any(word in q for word in ("인과", "구조", "흐름", "영향", "story")):
        return True, "structure"
    return False, None


def _comparison_chart_spec(evidence: list[EvidenceItem]) -> dict[str, Any] | None:
    byMetric: dict[str, list[EvidenceItem]] = {}
    for item in evidence:
        if not item.target or not item.metric:
            continue
        if _numeric_value(item.value) is None:
            continue
        byMetric.setdefault(str(item.metric), []).append(item)
    for metric, rows in byMetric.items():
        targets: dict[str, EvidenceItem] = {}
        for item in rows:
            targets.setdefault(str(item.target), item)
        if len(targets) < 2:
            continue
        picked = list(targets.values())[:12]
        return {
            "vizType": "chart",
            "chartType": "bar",
            "title": f"Comparison: {metric}",
            "categories": [str(item.target) for item in picked],
            "series": [{"name": metric, "data": [_numeric_value(item.value) for item in picked]}],
            "options": {"unit": picked[0].unit},
            "meta": {"generated": "workspace", "basis": "same_metric_evidence"},
        }
    return None


def _diagram_spec(evidence: list[EvidenceItem], title: str) -> dict[str, Any] | None:
    targets = [
        str(v) for v in sorted({item.target for item in evidence if item.target}) if _meaningful_diagram_target(str(v))
    ][:8]
    if len(targets) < 2:
        return None
    lines = ["graph LR"]
    for target in targets:
        safe = re.sub(r"[^0-9A-Za-z가-힣_]+", "_", target).strip("_") or "target"
        lines.append(f"  evidence[{target}] --> {safe}[{target}]")
    return {
        "vizType": "diagram",
        "diagramType": "mermaid",
        "title": title[:80] if title else "Evidence map",
        "source": "\n".join(lines),
        "meta": {"generated": "workspace", "basis": "evidence_map"},
    }


def _meaningful_diagram_target(value: str) -> bool:
    text = value.strip()
    if len(text) < 2:
        return False
    lowered = text.lower()
    if lowered in {"int64", "float64", "str", "string", "object", "none", "true", "false"}:
        return False
    if re.fullmatch(r"\d+(?:\.\d+)?", text):
        return False
    return True


def _numeric_value(value: Any) -> float | int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        raw = value.replace(",", "").replace("%", "").strip()
        try:
            return float(raw)
        except ValueError:
            return None
    return None


def _required_evidence_satisfied(required: list[str], observed: set[str], workspace: AnalysisWorkspace) -> bool:
    return _required_evidence_coverage(required, observed, workspace) >= 1


def _required_evidence_coverage(required: list[str], observed: set[str], workspace: AnalysisWorkspace) -> float:
    if not required:
        return 1.0
    contracts = set(workspace.coverage.get("contractIds") or [])
    if "comparison.same_axis" in contracts:
        matrix = workspace.coverage.get("matrix") or {}
        if isinstance(matrix, dict) and len(matrix) >= 2 and "metric" in observed:
            return 1.0
    normalized = {key.lower(): key for key in observed}
    satisfied = 0
    for key in required:
        lowered = key.lower()
        if lowered in normalized:
            satisfied += 1
            continue
        if lowered == "asof" and (workspace.freshness or "period" in observed):
            satisfied += 1
            continue
        if lowered == "universe" and len(workspace.evidence) >= 10:
            satisfied += 1
            continue
        if lowered == "period" and workspace.freshness:
            satisfied += 1
            continue
    return _ratio(satisfied, len(required))


def _artifact_required(packet: dict[str, Any]) -> bool:
    return bool(packet.get("artifactPolicy", {}).get("primaryCsv"))


def _merge_process_values(process_maps: list[dict[str, Any]], key: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for process in process_maps:
        value = process.get(key) if isinstance(process, dict) else None
        if isinstance(value, dict):
            out.update(value)
    return out


def _compact_args(args: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in (args or {}).items():
        if key in {"api_key", "apiKey", "password", "token", "secret"}:
            safe[str(key)] = "<redacted>"
            continue
        if key == "code":
            text = str(value)
            safe[str(key)] = {"chars": len(text), "preview": text[:120]}
            continue
        safe[str(key)] = _json_safe(value)
    return safe


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 1.0
    return round(max(0.0, min(1.0, float(numerator) / float(denominator))), 4)


def _format_brief_value(value: Any, unit: str | None, basis: str | None) -> str:
    numeric = _numeric_value(value)
    if numeric is not None:
        if abs(float(numeric)) >= 1_000_000_000_000:
            text = f"{float(numeric) / 1_000_000_000_000:.2f}조"
        elif abs(float(numeric)) >= 100_000_000:
            text = f"{float(numeric) / 100_000_000:.2f}억"
        elif isinstance(numeric, float):
            text = f"{numeric:.4g}"
        else:
            text = str(numeric)
        if unit and unit not in {"price"} and not text.endswith(str(unit)):
            text += str(unit)
        return text
    if value not in (None, ""):
        return str(value)[:80]
    return str(basis or "근거 있음")[:80]


def _normalize_visual_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """Normalize visual specs through dartlab.viz while preserving SSE compatibility."""
    try:
        from dartlab.viz import VizSpec

        normalized = VizSpec.fromDict(spec).toDict()
    except Exception:  # noqa: BLE001 - visual normalization must not break answer generation
        normalized = dict(spec)
    normalized.setdefault("vizType", spec.get("vizType") or ("diagram" if normalized.get("diagramType") else "chart"))
    return normalized


def _cadence(args: dict[str, Any], item: EvidenceItem) -> str:
    target = str(args.get("target") or item.target or item.metric or "").upper()
    axis = str(args.get("axis") or "").lower()
    if axis in {"krx", "price", "krxindex"} or target in {"USDKRW", "KRWUSD", "DEXKOUS", "KOSPI", "KOSDAQ"}:
        return "daily"
    if target in {"BASE_RATE", "POLICY_RATE"}:
        return "policy"
    return "unknown"


def _is_stale_daily(args: dict[str, Any], item: EvidenceItem, asOf: date) -> bool:
    if _cadence(args, item) != "daily":
        return False
    return _business_days_between(asOf, date.today()) > 10


def _business_days_between(start: date, end: date) -> int:
    if start >= end:
        return 0
    count = 0
    current = start + timedelta(days=1)
    while current <= end:
        if current.weekday() < 5:
            count += 1
        current += timedelta(days=1)
    return count


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if value is None:
        return None
    match = re.search(r"(20\d{2})[-./](\d{1,2})[-./](\d{1,2})", str(value))
    if not match:
        return None
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


def _claim_sentences(answer: str) -> list[str]:
    text = re.sub(r"\|.*\|", " ", answer)
    candidates = re.split(r"(?<=[.!?。])\s+|\n+", text)
    out: list[str] = []
    for item in candidates:
        clean = re.sub(r"\s+", " ", item).strip(" -")
        if len(clean) < 12:
            continue
        if any(token in clean for token in ("판단", "결론", "보입니다", "입니다", "해야", "위험", "강점", "약점")):
            out.append(clean[:400])
    return out[:12]


def _looks_like_judgment(text: str) -> bool:
    return any(token in text for token in ("판단", "결론", "보입니다", "해야", "위험", "강점", "약점"))


def _is_number_like(value: Any) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        return bool(re.fullmatch(r"[-+]?\d+(?:\.\d+)?%?", value.replace(",", "").strip()))
    return False


def _json_safe(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (date,)):
        return value.isoformat()
    if hasattr(value, "to_dicts"):
        try:
            return _json_safe(value.to_dicts())
        except Exception:  # noqa: BLE001
            pass
    if hasattr(value, "tolist"):
        try:
            return _json_safe(value.tolist())
        except Exception:  # noqa: BLE001
            pass
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    try:
        return value.item()
    except Exception:  # noqa: BLE001
        return str(value)


def _drop_empty(data: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in data.items() if not _is_empty(v)}


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value == ""
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) == 0
    return False

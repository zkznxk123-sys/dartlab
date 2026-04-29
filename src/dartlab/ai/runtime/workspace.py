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

from dartlab.ai.runtime.contract_graph import contractForTool


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
        self.evidence: list[EvidenceItem] = []
        self.claims: list[ClaimItem] = []
        self.visuals: list[VisualItem] = []
        self.limits: list[str] = []
        self.coverage: dict[str, Any] = {}
        self.freshness: dict[str, Any] = {}
        self.latency: dict[str, Any] = {
            "llmRoundMs": [],
            "toolTotalMs": 0,
            "toolCalls": [],
            "rewriteCount": 0,
            "maxRoundsReached": False,
        }
        self.visualRequirement: dict[str, Any] = {"required": False, "satisfied": False}
        self._seq = 0
        self._claimRecorded = False

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
                self._observeEvidence(args, item)

        return self.evidence[before:]

    def recordVisualSpec(
        self,
        spec: dict[str, Any],
        *,
        purpose: str = "explain",
        evidenceIds: list[str] | None = None,
    ) -> VisualItem:
        vizType = str(spec.get("vizType") or ("diagram" if spec.get("diagramType") else "chart"))
        linked = list(evidenceIds or [e.id for e in self.evidence[-30:]])
        item = VisualItem(
            id=self._next_id("viz"),
            vizType=vizType,
            purpose=purpose,
            spec=_json_safe(spec),
            evidenceIds=linked,
            primary=not self.visuals,
        )
        self.visuals.append(item)
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
        return {
            "evidence": [e.toDict() for e in self.evidence],
            "claims": [c.toDict() for c in self.claims],
            "visuals": [v.toDict() for v in self.visuals],
            "limits": list(self.limits),
        }

    def summary(self) -> dict[str, Any]:
        return {
            "evidenceCount": len(self.evidence),
            "claimCount": len(self.claims),
            "visualCount": len(self.visuals),
            "limitCount": len(self.limits),
            "coverage": _drop_empty(_json_safe(self.coverage)),
            "freshness": _drop_empty(_json_safe(self.freshness)),
            "visualRequirement": _drop_empty(_json_safe(self.visualRequirement)),
            **self.latencySummary(),
        }

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
            return [_json_safe(r) for r in result.head(30).to_dicts()]
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
                rows.append(dict(zip(headers, cells, strict=True)))
            if rows:
                return rows
    return []


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
    targets = [str(v) for v in sorted({item.target for item in evidence if item.target})[:8]]
    if not targets:
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

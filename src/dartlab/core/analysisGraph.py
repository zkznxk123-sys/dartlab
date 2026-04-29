"""Analysis Graph lookup.

Analysis Graph is a generated index over the existing capability/docstring
surface. It is not a planner and does not own domain truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class QuestionProfile:
    """Machine-readable question shape used by selectors and gates."""

    types: tuple[str, ...] = ()

    def has(self, name: str) -> bool:
        return name in self.types


@dataclass(frozen=True)
class PreflightAction:
    """One graph-declared runtime action."""

    tool: str
    argsTemplate: dict[str, Any] = field(default_factory=dict)
    primaryEvidence: bool = False


@dataclass(frozen=True)
class CapabilityContract:
    """Resolved Analysis Graph contract metadata."""

    contractId: str
    tool: str | None = None
    questionTypes: tuple[str, ...] = ()
    requiredEvidence: tuple[str, ...] = ()
    evidenceSchema: dict[str, Any] = field(default_factory=dict)
    freshness: dict[str, Any] = field(default_factory=dict)
    comparisonCompleteness: dict[str, Any] = field(default_factory=dict)
    visualPolicy: dict[str, Any] = field(default_factory=dict)
    artifactPolicy: dict[str, Any] = field(default_factory=dict)
    toolArgPolicy: tuple[str, ...] = ()
    toolBudget: dict[str, Any] = field(default_factory=dict)
    preflightActions: tuple[PreflightAction, ...] = ()
    priority: int = 50
    sourceKey: str | None = None
    toolNames: tuple[str, ...] = ()

    def toDict(self) -> dict[str, Any]:
        return {
            "contractId": self.contractId,
            "tool": self.tool,
            "questionTypes": list(self.questionTypes),
            "requiredEvidence": list(self.requiredEvidence),
            "evidenceSchema": dict(self.evidenceSchema),
            "freshness": dict(self.freshness),
            "comparisonCompleteness": dict(self.comparisonCompleteness),
            "visualPolicy": dict(self.visualPolicy),
            "artifactPolicy": dict(self.artifactPolicy),
            "toolArgPolicy": list(self.toolArgPolicy),
            "toolBudget": dict(self.toolBudget),
            "preflightActions": [
                {
                    "tool": action.tool,
                    "argsTemplate": dict(action.argsTemplate),
                    "primaryEvidence": action.primaryEvidence,
                }
                for action in self.preflightActions
            ],
            "priority": self.priority,
            "sourceKey": self.sourceKey,
            "toolNames": list(self.toolNames),
        }


def graphStatus() -> dict[str, Any]:
    graph = loadAnalysisGraph()
    return {
        "graphVersion": graph.get("graphVersion"),
        "sourceHash": graph.get("sourceHash"),
        "nodeCount": len(graph.get("nodes") or []),
        "edgeCount": len(graph.get("edges") or []),
        "contractCount": len(graph.get("contracts") or {}),
        "routeCount": len(graph.get("routes") or []),
    }


def loadAnalysisGraph() -> dict[str, Any]:
    """Return generated Analysis Graph payload."""
    try:
        from dartlab.core._generated_analysis_graph import ANALYSIS_GRAPH

        return ANALYSIS_GRAPH
    except Exception:
        return {"graphVersion": 0, "sourceHash": "missing", "nodes": [], "edges": [], "contracts": {}, "routes": []}


def inferQuestionProfile(question: str | None) -> QuestionProfile:
    """Infer profile by matching generated graph route triggers."""
    q = (question or "").lower()
    types: list[str] = []
    for route in _routes():
        triggers = route.get("triggers") or {}
        if _matches_triggers(q, triggers):
            question_type = str(route.get("questionType") or "")
            if question_type:
                types.append(question_type)
    return QuestionProfile(tuple(dict.fromkeys(types)))


def routeQuestion(
    question: str | None,
    *,
    category: str = "finance",
    intent: str | None = None,
    stockCode: str | None = None,
) -> dict[str, Any]:
    """Resolve one request into graph route metadata."""
    profile = inferQuestionProfile(question)
    contract_ids = [contract.contractId for contract in contractsForQuestion(question)]
    if intent == "compare" and "comparison.same_axis" not in contract_ids:
        contract_ids.append("comparison.same_axis")
    if intent == "act3_cash" and "cashflow.primary" not in contract_ids:
        contract_ids.append("cashflow.primary")

    tools: list[str] = []
    route_ids: list[str] = []
    for route in _routes():
        if route.get("questionType") not in profile.types:
            continue
        route_ids.append(str(route.get("id")))
        for name in route.get("toolNames") or []:
            if name and name not in tools:
                tools.append(str(name))
    for contract_id in contract_ids:
        contract = allContracts().get(contract_id)
        if contract is None:
            continue
        for name in contract.toolNames or ([contract.tool] if contract.tool else []):
            if name and name not in tools:
                tools.append(str(name))

    return {
        "category": category,
        "intent": intent,
        "stockCode": stockCode,
        "profileTypes": list(profile.types),
        "routeIds": route_ids,
        "contractIds": contract_ids,
        "toolNames": tools,
        "graph": graphStatus(),
    }


def allContracts() -> dict[str, CapabilityContract]:
    """Return Analysis Graph contracts keyed by contractId."""
    out: dict[str, CapabilityContract] = {}
    for contract_id, raw in (loadAnalysisGraph().get("contracts") or {}).items():
        if not isinstance(raw, dict):
            continue
        parsed = _contract_from_graph(str(contract_id), raw)
        out[parsed.contractId] = parsed
    return out


def contractsForQuestion(question: str | None) -> list[CapabilityContract]:
    profile = inferQuestionProfile(question)
    if not profile.types:
        return []
    profile_types = set(profile.types)
    contracts = [contract for contract in allContracts().values() if set(contract.questionTypes) & profile_types]
    return sorted(contracts, key=lambda item: item.priority, reverse=True)


def contractIdsForQuestion(question: str | None) -> list[str]:
    return [contract.contractId for contract in contractsForQuestion(question)]


def contractForTool(name: str, arguments: dict[str, Any] | None = None) -> CapabilityContract | None:
    args = arguments or {}
    for contract in sorted(allContracts().values(), key=lambda item: item.priority, reverse=True):
        raw = _raw_contract(contract.contractId)
        for matcher in raw.get("toolMatch") or []:
            if _matches_tool(name, args, matcher):
                return contract
    for contract in allContracts().values():
        if contract.tool == name:
            return contract
    return None


def answerContractNames(question: str | None, toolCalls: list[dict[str, Any]]) -> set[str]:
    """Compatibility-level answer contract names derived from graph contracts."""
    contract_ids = set(contractIdsForQuestion(question))
    for call in toolCalls:
        args = call.get("arguments") or call.get("args") or {}
        if not isinstance(args, dict):
            args = {}
        contract = contractForTool(str(call.get("name") or ""), args)
        if contract:
            contract_ids.add(contract.contractId)

    names: set[str] = set()
    if contract_ids & {"gather.krx.close", "macro.recent"}:
        names.add("recent")
    if "comparison.same_axis" in contract_ids:
        names.add("comparison")
    if "disclosure.importance" in contract_ids:
        names.add("disclosure")
    if "capabilities.valid_key" in contract_ids:
        names.add("capabilities")
    return names


def preflightActionsForQuestion(
    *,
    question: str | None,
    category: str,
    intent: str | None,
    stockCode: str | None = None,
) -> list[tuple[str, dict[str, Any], CapabilityContract]]:
    if category != "finance":
        return []
    route = routeQuestion(question, category=category, intent=intent, stockCode=stockCode)
    actions: list[tuple[str, dict[str, Any], CapabilityContract]] = []
    for contract_id in route["contractIds"]:
        contract = allContracts().get(contract_id)
        if contract is None:
            continue
        for action in contract.preflightActions:
            args = dict(action.argsTemplate)
            if action.tool in {"analysis", "show"} and stockCode and contract.contractId != "comparison.same_axis":
                args.setdefault("stockCode", stockCode)
            if (
                action.tool in {"analysis", "show"}
                and contract.contractId != "comparison.same_axis"
                and not args.get("stockCode")
            ):
                continue
            actions.append((action.tool, args, contract))
    return actions


def toolBudgetForQuestion(question: str | None, intent: str | None) -> dict[str, Any]:
    route = routeQuestion(question, intent=intent)
    budget: dict[str, Any] = {}
    for contract_id in route["contractIds"]:
        contract = allContracts().get(contract_id)
        if contract is not None:
            budget.update(contract.toolBudget)
    return budget


def toolNamesForQuestion(question: str | None, *, intent: str | None = None) -> list[str]:
    return [str(v) for v in routeQuestion(question, intent=intent).get("toolNames") or []]


def requiresVisualExplanation(question: str | None) -> bool:
    for contract in contractsForQuestion(question):
        policy = contract.visualPolicy or {}
        if policy.get("requiredFor"):
            return True
    return False


def contextForQuestion(question: str, stockCode: str | None = None) -> dict[str, Any]:
    """MCP-facing compact route context."""
    route = routeQuestion(question, stockCode=stockCode)
    return {
        "question": question,
        "route": route,
        "contracts": [allContracts()[cid].toDict() for cid in route["contractIds"] if cid in allContracts()],
    }


def queryAnalysisGraph(query: str, *, kind: str | None = None, topK: int = 10) -> list[dict[str, Any]]:
    """Simple graph search over node labels, ids, contract ids, and sources."""
    q = query.lower().strip()
    if not q:
        return []
    rows: list[dict[str, Any]] = []
    graph = loadAnalysisGraph()
    for node in graph.get("nodes") or []:
        if kind and node.get("kind") != kind:
            continue
        haystack = " ".join(str(node.get(k) or "") for k in ("id", "kind", "label", "source")).lower()
        if q in haystack:
            rows.append({"score": 1.0, **node})
    for contract_id, contract in (graph.get("contracts") or {}).items():
        haystack = " ".join(
            str(contract.get(k) or "") for k in ("contractId", "tool", "summary", "sourceKey", "questionTypes")
        ).lower()
        if q in haystack:
            rows.append(
                {
                    "score": 0.9,
                    "id": f"contract:{contract_id}",
                    "kind": "contract",
                    "label": contract.get("summary") or contract_id,
                    "source": contract.get("sourceKey"),
                }
            )
    return rows[: max(1, min(int(topK or 10), 50))]


def impactForGraphNode(nodeId: str) -> dict[str, Any]:
    """Return graph edges adjacent to one node."""
    graph = loadAnalysisGraph()
    edges = [
        edge
        for edge in graph.get("edges") or []
        if isinstance(edge, dict) and (edge.get("from") == nodeId or edge.get("to") == nodeId)
    ]
    return {"nodeId": nodeId, "edges": edges, "edgeCount": len(edges)}


def _routes() -> list[dict[str, Any]]:
    return [route for route in loadAnalysisGraph().get("routes") or [] if isinstance(route, dict)]


def _raw_contract(contract_id: str) -> dict[str, Any]:
    raw = (loadAnalysisGraph().get("contracts") or {}).get(contract_id) or {}
    return raw if isinstance(raw, dict) else {}


def _contract_from_graph(contract_id: str, entry: dict[str, Any]) -> CapabilityContract:
    preflights: list[PreflightAction] = []
    for raw in entry.get("preflightActions") or []:
        if isinstance(raw, dict) and raw.get("tool"):
            preflights.append(
                PreflightAction(
                    str(raw.get("tool")),
                    dict(raw.get("argsTemplate") or {}),
                    bool(raw.get("primaryEvidence")),
                )
            )
    return CapabilityContract(
        contractId=str(entry.get("contractId") or contract_id),
        tool=entry.get("tool"),
        questionTypes=tuple(str(v) for v in entry.get("questionTypes") or ()),
        requiredEvidence=tuple(str(v) for v in entry.get("requiredEvidence") or ()),
        evidenceSchema=dict(entry.get("evidenceSchema") or {}),
        freshness=dict(entry.get("freshness") or {}),
        comparisonCompleteness=dict(entry.get("comparisonCompleteness") or {}),
        visualPolicy=dict(entry.get("visualPolicy") or {}),
        artifactPolicy=dict(entry.get("artifactPolicy") or {}),
        toolArgPolicy=tuple(str(v) for v in entry.get("toolArgPolicy") or ()),
        toolBudget=dict(entry.get("toolBudget") or {}),
        preflightActions=tuple(preflights),
        priority=int(entry.get("priority") or 50),
        sourceKey=str(entry.get("sourceKey") or "") or None,
        toolNames=tuple(str(v) for v in entry.get("toolNames") or ()),
    )


def _matches_triggers(q: str, triggers: dict[str, Any]) -> bool:
    if not triggers:
        return False
    any_terms = [str(v).lower() for v in triggers.get("any") or []]
    if any_terms and any(term in q for term in any_terms):
        return True
    all_any = triggers.get("allAny") or []
    if all_any:
        for group in all_any:
            terms = [str(v).lower() for v in group or []]
            if not terms or not any(term in q for term in terms):
                return False
        return True
    return False


def _matches_tool(name: str, args: dict[str, Any], matcher: dict[str, Any]) -> bool:
    if str(matcher.get("tool") or "") != name:
        return False
    arg_rules = matcher.get("args") or {}
    if not isinstance(arg_rules, dict):
        return True
    for key, expected in arg_rules.items():
        if key.endswith("In"):
            arg_key = key[:-2]
            values = {str(v).lower() for v in expected or []}
            if str(args.get(arg_key) or "").lower() not in values:
                return False
            continue
        if str(args.get(key) or "").lower() != str(expected).lower():
            return False
    return True

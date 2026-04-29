"""Capability Contract Graph lookup for AI runtime.

The contract content lives in generated CAPABILITIES metadata.  This module
only resolves that metadata for runtime consumers.
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
    """One contract-declared runtime action."""

    tool: str
    argsTemplate: dict[str, Any] = field(default_factory=dict)
    primaryEvidence: bool = False


@dataclass(frozen=True)
class CapabilityContract:
    """Resolved generated contract metadata consumed by runtime components."""

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
        }


_PRICE_MOVER_WORDS = ("오른", "상승", "급등", "수익률", "모멘텀", "mover", "return", "ranking", "rank")
_PRICE_TARGET_WORDS = ("주가", "가격", "종목", "price", "stock")
_COMPARISON_WORDS = ("비교", "대비", "vs", " versus ", "둘 중", "어느 쪽", "누가", "경쟁력")
_DISCLOSURE_WORDS = ("공시", "filing", "dart", "보고서")
_CASHFLOW_WORDS = ("현금흐름", "cashflow", "cash flow", "fcf", "ocf")
_STORY_WORDS = ("기업이야기", "스토리", "story", "서사")
_RECENT_WORDS = ("최근", "현재", "오늘", "어제", "latest", "recent", "지금")
_META_WORDS = ("뭐 할 수", "어떻게 써", "사용법", "help", "capabilities")


def inferQuestionProfile(question: str | None) -> QuestionProfile:
    """Infer a compact profile without choosing tools by itself."""
    q = (question or "").lower()
    types: list[str] = []
    if any(word in q for word in _PRICE_TARGET_WORDS) and any(word in q for word in _PRICE_MOVER_WORDS):
        types.append("recent_price_mover")
    if any(word in q for word in _COMPARISON_WORDS):
        types.append("company_compare")
    if any(word in q for word in _DISCLOSURE_WORDS):
        types.append("disclosure_importance")
    if any(word in q for word in _CASHFLOW_WORDS):
        types.append("cashflow")
    if any(word in q for word in _RECENT_WORDS) and any(word in q for word in ("금리", "환율", "fx", "rate", "macro")):
        types.append("macro_recent")
    if any(word in q for word in _STORY_WORDS):
        types.append("story")
    if any(word in q for word in _META_WORDS):
        types.append("meta_help")
    return QuestionProfile(tuple(dict.fromkeys(types)))


def allContracts() -> dict[str, CapabilityContract]:
    """Return generated AI contracts keyed by contractId."""
    contracts: dict[str, CapabilityContract] = {}
    for key, entry in _generated_capabilities().items():
        parsed = _contract_from_capability(key, entry)
        if parsed is not None:
            contracts[parsed.contractId] = parsed
    return contracts


def contractsForQuestion(question: str | None) -> list[CapabilityContract]:
    profile = inferQuestionProfile(question)
    if not profile.types:
        return []
    return sorted(
        [contract for contract in allContracts().values() if set(contract.questionTypes) & set(profile.types)],
        key=lambda item: item.priority,
        reverse=True,
    )


def contractForTool(name: str, arguments: dict[str, Any] | None = None) -> CapabilityContract | None:
    contract_id = _contract_id_for_tool(name, arguments or {})
    contracts = allContracts()
    if contract_id:
        return contracts.get(contract_id)
    for contract in contracts.values():
        if contract.tool == name:
            return contract
    return None


def contractIdsForQuestion(question: str | None) -> list[str]:
    return [contract.contractId for contract in contractsForQuestion(question)]


def legacyAnswerContractNames(question: str | None, toolCalls: list[dict[str, Any]]) -> set[str]:
    """Compatibility names used by existing quality checks."""
    ids = set(contractIdsForQuestion(question))
    names: set[str] = set()
    if any(cid in ids for cid in ("gather.krx.close", "macro.recent")):
        names.add("recent")
    if "comparison.same_axis" in ids:
        names.add("comparison")
    if "disclosure.importance" in ids:
        names.add("disclosure")
    for call in toolCalls:
        name = str(call.get("name", ""))
        args = call.get("arguments") or call.get("args") or {}
        if not isinstance(args, dict):
            args = {}
        contract = contractForTool(name, args)
        if contract is None:
            continue
        if contract.contractId in {"gather.krx.close", "macro.recent"}:
            names.add("recent")
        if contract.contractId == "disclosure.importance":
            names.add("disclosure")
        if contract.contractId == "capabilities.valid_key":
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
    actions: list[tuple[str, dict[str, Any], CapabilityContract]] = []
    for contract in contractsForQuestion(question):
        for action in contract.preflightActions:
            args = dict(action.argsTemplate)
            if action.tool in {"analysis", "show"} and stockCode and contract.contractId != "comparison.same_axis":
                args.setdefault("stockCode", stockCode)
            if (
                not args.get("stockCode")
                and action.tool in {"analysis", "show"}
                and contract.contractId != "comparison.same_axis"
            ):
                continue
            actions.append((action.tool, args, contract))
    if intent == "act3_cash" and not any(c.contractId == "cashflow.primary" for _, _, c in actions):
        contract = allContracts().get("cashflow.primary")
        if contract is not None:
            for action in contract.preflightActions:
                if stockCode:
                    args = dict(action.argsTemplate)
                    args.setdefault("stockCode", stockCode)
                    actions.append((action.tool, args, contract))
    return actions


def toolBudgetForQuestion(question: str | None, intent: str | None) -> dict[str, Any]:
    budget: dict[str, Any] = {}
    for contract in contractsForQuestion(question):
        budget.update(contract.toolBudget)
    if intent == "compare":
        compare = allContracts().get("comparison.same_axis")
        if compare is not None:
            budget.update(compare.toolBudget)
    return budget


def _contract_id_for_tool(name: str, args: dict[str, Any]) -> str | None:
    if name == "gather":
        axis = str(args.get("axis") or "").lower()
        target = str(args.get("target") or "").lower()
        if axis == "krx" and target in {"", "close", "raw"}:
            return "gather.krx.close"
        if axis == "macro":
            return "macro.recent"
    if name in {"search", "filings", "liveFilings", "disclosure"}:
        return "disclosure.importance"
    if name == "capabilities":
        return "capabilities.valid_key"
    return None


def _generated_capabilities() -> dict[str, dict[str, Any]]:
    try:
        from dartlab.core._generated import CAPABILITIES

        return CAPABILITIES
    except Exception:
        return {}


def _contract_from_capability(key: str, entry: dict[str, Any]) -> CapabilityContract | None:
    raw_id = entry.get("contractId") or entry.get("contract_id")
    if not raw_id:
        return None
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
        contractId=str(raw_id),
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
    )

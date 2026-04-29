"""Compatibility shim for the generated Analysis Graph.

Runtime contract lookup now lives in :mod:`dartlab.core.analysisGraph` so AI
runtime and MCP clients read the same graph.
"""

from __future__ import annotations

from dartlab.core.analysisGraph import (
    CapabilityContract,
    PreflightAction,
    QuestionProfile,
    allContracts,
    answerContractNames,
    contractForTool,
    contractIdsForQuestion,
    contractsForQuestion,
    graphStatus,
    inferQuestionProfile,
    preflightActionsForQuestion,
    requiresVisualExplanation,
    routeQuestion,
    toolBudgetForQuestion,
    toolNamesForQuestion,
)

legacyAnswerContractNames = answerContractNames

__all__ = [
    "CapabilityContract",
    "PreflightAction",
    "QuestionProfile",
    "allContracts",
    "answerContractNames",
    "contractForTool",
    "contractIdsForQuestion",
    "contractsForQuestion",
    "graphStatus",
    "inferQuestionProfile",
    "legacyAnswerContractNames",
    "preflightActionsForQuestion",
    "requiresVisualExplanation",
    "routeQuestion",
    "toolBudgetForQuestion",
    "toolNamesForQuestion",
]

"""Canonical DartLab AI tools."""

from dataclasses import dataclass
from typing import Any

from .registry import CANONICAL_TOOL_NAMES, executeTool, listToolNames, registerTool, toolSpecs, unregisterTool
from .types import ToolResult, ToolSpec


@dataclass(frozen=True)
class _LegacyTool:
    name: str
    description: str
    parameters: dict[str, Any]


def buildTools() -> list[_LegacyTool]:
    """Legacy tool list shim retained for older validation tests."""
    validateStory = _LegacyTool(
        name="validateStory",
        description="Validate story assumptions and valuation override inputs.",
        parameters={
            "type": "object",
            "properties": {
                "overrides": {
                    "type": "object",
                    "description": (
                        "Optional valuation overrides: impliedERP, bottomUpBeta, lifeCyclePhase, "
                        "pSurvival, countryCode, wacc, terminalGrowth, growthRates, marginPath, "
                        "reinvestmentPath."
                    ),
                    "additionalProperties": True,
                }
            },
        },
    )
    return [
        _LegacyTool(name=spec["name"], description=spec["description"], parameters=spec["inputSchema"])
        for spec in toolSpecs()
    ] + [validateStory]


__all__ = [
    "CANONICAL_TOOL_NAMES",
    "ToolResult",
    "ToolSpec",
    "buildTools",
    "executeTool",
    "listToolNames",
    "registerTool",
    "toolSpecs",
    "unregisterTool",
]

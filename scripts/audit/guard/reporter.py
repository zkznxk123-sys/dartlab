"""Guard 결과 출력."""

from __future__ import annotations

import json
from typing import Any


def printConsole(result: dict[str, Any]) -> None:
    """사람용 Guard 요약 출력."""
    summary = result["summary"]
    print("=== DartLab Guard Index ===")
    print(f"status       : {summary['status']}")
    print(f"scope        : {result['scope']}")
    print(f"providers    : {', '.join(result['providers'])}")
    print(f"files scanned: {summary['filesScanned']}")
    print(f"rules passed : {summary['rulesPassed']}")
    print(f"rules failed : {summary['rulesFailed']}")
    baseline = result.get("baseline", {})
    staleKnown = baseline.get("staleKnown") or []
    knownViolations = baseline.get("knownViolations") or []
    if knownViolations:
        print(f"known debt   : {len(knownViolations)} (baseline ledger)")
    if staleKnown:
        print(f"stale known  : {len(staleKnown)} (baseline shrink 필요)")
    if result["violations"]:
        print("\n[violations]")
        for item in result["violations"][:20]:
            print(f"- {item['rule']} {item['path']}:{item['line']} {item['message']}")
        if len(result["violations"]) > 20:
            print(f"... {len(result['violations']) - 20} more")
    if result["externalGates"]:
        print("\n[external gates]")
        for gate in result["externalGates"]:
            print(f"- {gate['status'].upper()} {gate['name']} ({gate['durationMs']} ms)")
            if gate["status"] != "pass" and gate.get("outputTail"):
                print(gate["outputTail"])


def printJson(result: dict[str, Any]) -> None:
    """machine-readable Guard 결과 출력."""
    print(json.dumps(result, indent=2, ensure_ascii=False))

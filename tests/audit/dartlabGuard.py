"""DartLab Guard Index — AST 전수조사 + 기존 audit gate 통합 표면."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_THIS = Path(__file__).resolve()
_AUDIT_DIR = _THIS.parent
_REPO = _THIS.parents[2]
sys.path.insert(0, str(_AUDIT_DIR))

from guard.baseline import compareBaseline, loadBaseline  # noqa: E402
from guard.indexer import buildIndex  # noqa: E402
from guard.reporter import printConsole, printJson  # noqa: E402
from guard.rules import evaluateL0L15  # noqa: E402
from guard.runner import changedFiles, fullGates, l0L15Gates, quickGates  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = buildParser()
    args = parser.parse_args(argv)
    try:
        result = runGuard(args)
    except (FileNotFoundError, ValueError) as exc:
        if args.json:
            printJson({"version": 1, "summary": {"status": "error"}, "error": str(exc)})
        else:
            print(f"[dartlabGuard] {exc}", file=sys.stderr)
        return 2
    if args.index_out:
        Path(args.index_out).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    if args.json:
        printJson(result)
    else:
        printConsole(result)
    return 0 if result["summary"]["status"] == "pass" else 1


def buildParser() -> argparse.ArgumentParser:
    """argparse parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("quick", "strict", "full"))
    parser.add_argument("--scope", default="l0-l15", choices=("l0-l15", "all"))
    parser.add_argument(
        "--providers",
        default="dart,edgar",
        help="쉼표 구분 provider scope. 기본 dart,edgar. edinet 은 deferred.",
    )
    parser.add_argument("--baseline", default="tests/audit/_baselines/dartlabGuard.json")
    parser.add_argument("--json", action="store_true", help="machine-readable JSON 출력")
    parser.add_argument("--changed-from", default="HEAD~1", help="quick 모드 변경 기준")
    parser.add_argument("--index-out", default=None, help="Guard result JSON 저장 경로")
    return parser


def runGuard(args: argparse.Namespace) -> dict[str, Any]:
    """Guard 실행."""
    providerList = tuple(item.strip() for item in args.providers.split(",") if item.strip())
    records = buildIndex(_REPO)
    violations = evaluateL0L15(records) if args.scope in ("l0-l15", "all") else []
    baselinePath = (_REPO / args.baseline).resolve()
    baseline = loadBaseline(baselinePath)
    baselineResult = compareBaseline(violations, baseline)
    externalGates = selectExternalGates(args, providerList)
    failedExternal = [gate for gate in externalGates if gate.status != "pass"]
    status = "pass" if not baselineResult.newViolations and not failedExternal else "fail"
    failedRuleCount = len(baselineResult.newViolations) + len(failedExternal)
    result = {
        "version": 1,
        "root": str(_REPO),
        "scope": args.scope,
        "providers": list(providerList),
        "summary": {
            "status": status,
            "filesScanned": len(records),
            "rulesPassed": 1 + len(externalGates) - len(failedExternal),
            "rulesFailed": failedRuleCount,
            "activeKnownDebt": len(baselineResult.activeKnownViolations),
            "protectedCompanyFacadeDebt": len(baselineResult.protectedCompanyFacadeDebt),
        },
        "modules": [record.toDict() for record in records],
        "violations": [item.toDict() for item in baselineResult.newViolations],
        "baseline": baselineResult.toDict(),
        "externalGates": [gate.toDict() for gate in externalGates],
    }
    if args.command == "quick":
        result["changedFiles"] = changedFiles(_REPO, args.changed_from)
    return result


def selectExternalGates(args: argparse.Namespace, providerList: tuple[str, ...]) -> list[Any]:
    """command별 외부 gate 선택."""
    providers = ",".join(providerList)
    if args.command == "quick":
        files = changedFiles(_REPO, args.changed_from)
        return quickGates(_REPO, files, providers)
    if args.command == "strict":
        if args.scope != "l0-l15":
            raise ValueError("strict v1 supports --scope l0-l15 only")
        return l0L15Gates(_REPO, providers)
    if args.command == "full":
        return fullGates(_REPO, providers)
    raise ValueError(f"unknown command: {args.command}")


if __name__ == "__main__":
    sys.exit(main())

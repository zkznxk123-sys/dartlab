"""withMemoryBudget 공개 시나리오 매핑 감사.

함수 단위 RSS 가드는 유용하지만, 예산 값이 제품 시나리오 예산과 따로 놀면
이번 scanAccount 사고처럼 실제 사용자 호출에서 실패한다. 이 스크립트는
decorator가 붙은 공개 경로가 product smoke 시나리오와 resource budget을
갖는지 확인한다.
"""

from __future__ import annotations

import ast
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src" / "dartlab"
MANIFEST_PATH = REPO_ROOT / "tests" / "audit" / "publicApiScenarios.yml"
BUDGET_PATH = REPO_ROOT / "tests" / "audit" / "resourceBudgets.json"


@dataclass(frozen=True)
class MemoryBudgetUse:
    path: Path
    function: str
    line: int
    limit: str

    @property
    def rel(self) -> str:
        return self.path.relative_to(REPO_ROOT).as_posix()


PUBLIC_MEMORY_FUNCTIONS: dict[tuple[str, str], list[str]] = {
    ("src/dartlab/providers/dart/finance/scanAccount.py", "scanAccount"): ["scan.account.sales"],
    ("src/dartlab/providers/dart/finance/scanAccount.py", "scanRatio"): ["scan.ratio.roe"],
}


def _decoratorName(node: ast.AST) -> str | None:
    target = node.func if isinstance(node, ast.Call) else node
    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.Attribute):
        return target.attr
    return None


def _decoratorLimit(node: ast.AST) -> str:
    if not isinstance(node, ast.Call):
        return ""
    if node.args:
        return ast.unparse(node.args[0])
    for kw in node.keywords:
        if kw.arg == "limitMb":
            return ast.unparse(kw.value)
    return ""


def _scanFile(path: Path) -> list[MemoryBudgetUse]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    uses: list[MemoryBudgetUse] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if _decoratorName(decorator) == "withMemoryBudget":
                uses.append(
                    MemoryBudgetUse(
                        path=path,
                        function=node.name,
                        line=node.lineno,
                        limit=_decoratorLimit(decorator),
                    )
                )
    return uses


def _scanRepo() -> list[MemoryBudgetUse]:
    uses: list[MemoryBudgetUse] = []
    for path in SRC_ROOT.rglob("*.py"):
        uses.extend(_scanFile(path))
    return sorted(uses, key=lambda item: (item.rel, item.line))


def _loadYaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise SystemExit(f"YAML 형식 오류: {path}")
    return data


def _loadBudgets(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise SystemExit(f"JSON 형식 오류: {path}")
    return data


def audit() -> int:
    manifest = _loadYaml(MANIFEST_PATH)
    budgets = _loadBudgets(BUDGET_PATH)
    scenarios = manifest.get("scenarios", {})
    budgetKeys = set((budgets.get("scenarios") or {}).keys())
    failures: list[str] = []
    uses = _scanRepo()

    for use in uses:
        key = (use.rel, use.function)
        scenarioIds = PUBLIC_MEMORY_FUNCTIONS.get(key, [])
        if not scenarioIds:
            continue
        for scenarioId in scenarioIds:
            scenario = scenarios.get(scenarioId)
            if scenario is None:
                failures.append(f"{use.rel}:{use.line} {use.function}: scenario 없음: {scenarioId}")
                continue
            budgetKey = scenario.get("budget", scenarioId)
            if budgetKey not in budgetKeys:
                failures.append(f"{scenarioId}: resource budget 없음: {budgetKey}")

    if failures:
        print("[memory-budget-audit] 실패", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1

    print(f"[memory-budget-audit] OK withMemoryBudget={len(uses)} publicMapped={len(PUBLIC_MEMORY_FUNCTIONS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(audit())

"""Sync landing finance account order metadata from DartLab account SSOT."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SORT_ORDER_PATH = REPO_ROOT / "src" / "dartlab" / "core" / "utils" / "sortOrder.json"
ACCOUNT_MAPPINGS_PATH = REPO_ROOT / "src" / "dartlab" / "reference" / "data" / "accountMappings.json"
TARGET_PATH = REPO_ROOT / "landing" / "src" / "lib" / "viewer" / "finance" / "accountOrder.ts"

STATEMENTS = ("BS", "IS", "CF")
IDLIKE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
PREFIX_RE = re.compile(r"^(?:ifrs-full_|ifrs_|dart_|ifrs-smes_)")


def _loadJson(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _orderedStatementMaps(sortData: dict[str, Any]) -> tuple[dict[str, dict[str, int]], dict[str, dict[str, int]]]:
    orders: dict[str, dict[str, int]] = {}
    levels: dict[str, dict[str, int]] = {}
    for stmt in STATEMENTS:
        rows = sortData.get(stmt, {})
        sortedItems = sorted(rows.items(), key=lambda item: item[1].get("sortOrder", 9999))
        orders[stmt] = {snakeId: i for i, (snakeId, _) in enumerate(sortedItems)}
        levels[stmt] = {snakeId: int(meta.get("level", 1)) for snakeId, meta in rows.items()}
    return orders, levels


def _depthMaps(sortData: dict[str, Any]) -> dict[str, dict[str, int]]:
    """들여쓰기 깊이 — SSOT level 만 반영(강조와 분리). level 0=루트(BS 총계), 그 외 clamp(1..3)."""
    depths: dict[str, dict[str, int]] = {}
    for stmt in STATEMENTS:
        rows = sortData.get(stmt, {})
        stmtDepths: dict[str, int] = {}
        for snakeId, meta in rows.items():
            level = int(meta.get("level", 1))
            stmtDepths[snakeId] = 0 if level <= 0 else max(1, min(level, 3))
        depths[stmt] = stmtDepths
    return depths


def _isTotalMaps(sortData: dict[str, Any], accounts: dict[str, Any]) -> dict[str, dict[str, bool]]:
    """총계 강조(굵게+상단보더) 여부 — depth 와 분리. SSOT isTotal(IS 당기순이익/총포괄손익) +
    total_ 접두/'총계' 라벨 휴리스틱(BS 자산·부채·자본총계, 포괄손익 귀속 합계). True 항목만 수록."""
    standardAccounts: dict[str, dict[str, Any]] = accounts.get("standardAccounts", {})
    totals: dict[str, dict[str, bool]] = {}
    for stmt in STATEMENTS:
        rows = sortData.get(stmt, {})
        stmtTotals: dict[str, bool] = {}
        for snakeId, meta in rows.items():
            label = standardAccounts.get(snakeId, {}).get("korName", "")
            if meta.get("isTotal") or snakeId.startswith("total_") or "총계" in label:
                stmtTotals[snakeId] = True
        totals[stmt] = stmtTotals
    return totals


def _idMap(accounts: dict[str, Any], validSnakeIds: set[str]) -> dict[str, str]:
    mappings: dict[str, str] = accounts.get("mappings", {})
    out: dict[str, str] = {}

    for key, snakeId in mappings.items():
        stripped = PREFIX_RE.sub("", key)
        if snakeId in validSnakeIds and IDLIKE_RE.match(stripped):
            out[stripped] = snakeId

    for key, mappedKey in accounts.get("layers", {}).get("idSynonym", {}).items():
        stripped = PREFIX_RE.sub("", key)
        snakeId = mappings.get(mappedKey)
        if snakeId in validSnakeIds and IDLIKE_RE.match(stripped):
            out[stripped] = snakeId

    return dict(sorted(out.items()))


def _nameCandidates(accounts: dict[str, Any], validSnakeIds: set[str]) -> dict[str, list[str]]:
    buckets: dict[str, set[str]] = {}
    for snakeId, meta in accounts.get("standardAccounts", {}).items():
        label = meta.get("korName")
        if snakeId in validSnakeIds and isinstance(label, str) and label:
            buckets.setdefault(label, set()).add(snakeId)

    return {label: sorted(snakes) for label, snakes in sorted(buckets.items())}


def buildModel() -> dict[str, Any]:
    sortData = _loadJson(SORT_ORDER_PATH)
    accounts = _loadJson(ACCOUNT_MAPPINGS_PATH)
    orders, levels = _orderedStatementMaps(sortData)
    validSnakeIds = {snakeId for rows in orders.values() for snakeId in rows}
    return {
        "orders": orders,
        "levels": levels,
        "depths": _depthMaps(sortData),
        "isTotal": _isTotalMaps(sortData, accounts),
        "idMap": _idMap(accounts, validSnakeIds),
        "nameCandidates": _nameCandidates(accounts, validSnakeIds),
    }


def _tsConst(name: str, value: Any) -> str:
    body = json.dumps(value, ensure_ascii=False, indent="\t", sort_keys=True)
    return f"export const {name} = {body} as const;\n"


def render(model: dict[str, Any]) -> str:
    return (
        "// Mirrors DartLab account ordering metadata for the browser finance viewer.\n"
        "// Source: src/dartlab/core/utils/sortOrder.json + src/dartlab/reference/data/accountMappings.json\n\n"
        "export type FinanceStatementOrderKey = 'BS' | 'IS' | 'CF';\n\n"
        + _tsConst("FINANCE_ACCOUNT_ORDER", model["orders"])
        + "\n"
        + _tsConst("FINANCE_ACCOUNT_LEVEL", model["levels"])
        + "\n"
        + _tsConst("FINANCE_ACCOUNT_DEPTH", model["depths"])
        + "\n"
        + _tsConst("FINANCE_ACCOUNT_IS_TOTAL", model["isTotal"])
        + "\n"
        + _tsConst("FINANCE_ACCOUNT_ID_TO_SNAKE", model["idMap"])
        + "\n"
        + _tsConst("FINANCE_ACCOUNT_NAME_TO_SNAKES", model["nameCandidates"])
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if target is not synced")
    args = parser.parse_args(argv)

    text = render(buildModel())
    if args.check:
        current = TARGET_PATH.read_text(encoding="utf-8") if TARGET_PATH.exists() else ""
        if current != text:
            print(f"{TARGET_PATH} is out of sync", file=sys.stderr)
            return 1
        return 0

    TARGET_PATH.parent.mkdir(parents=True, exist_ok=True)
    TARGET_PATH.write_text(text, encoding="utf-8")
    print(f"synced {TARGET_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

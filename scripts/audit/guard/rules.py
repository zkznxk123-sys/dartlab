"""Guard Index rule 평가."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from guard.indexer import LAYER_OF, ROOT_FACADE, ModuleRecord

SINK_HELPERS = {"viz", "cli", "server", "channel"}
STRICT_L0_L15 = {"core", "gather", "providers", "scan", "frame", "synth", "reference"}
L1_PEERS = {"gather", "providers"}
L15_PEERS = {"scan", "frame", "synth", "reference"}
L2_PEERS = {"analysis", "macro", "quant", "industry", "credit"}


@dataclass(frozen=True)
class Violation:
    """Guard 위반 1건."""

    rule: str
    path: str
    line: int
    message: str
    severity: str
    baselineKey: str

    def toDict(self) -> dict[str, Any]:
        """JSON 직렬화용 dict."""
        return asdict(self)


def evaluateL0L15(records: list[ModuleRecord]) -> list[Violation]:
    """L0~L1.5 architecture rule 전수 평가."""
    violations: list[Violation] = []
    violations.extend(checkImportDirection(records))
    violations.extend(checkL1CrossImport(records))
    violations.extend(checkL15SiblingImport(records))
    violations.extend(checkLazyBoundaryDebt(records))
    return sorted(violations, key=lambda item: (item.rule, item.path, item.line, item.message))


def checkImportDirection(records: list[ModuleRecord]) -> list[Violation]:
    """L0~L1.5 상위 계층 직접 import 금지."""
    violations: list[Violation] = []
    for record in records:
        if record.topPackage not in STRICT_L0_L15:
            continue
        if record.path.endswith("/di.py") or record.path.endswith("\\di.py"):
            continue
        ownerLayer = LAYER_OF.get(record.topPackage)
        if ownerLayer is None:
            continue
        for importRecord in record.imports:
            if not importRecord.isTopLevel:
                continue
            target = importRecord.topPackage
            if target is None or target in SINK_HELPERS or target not in LAYER_OF:
                continue
            targetLayer = LAYER_OF[target]
            if targetLayer > ownerLayer:
                violations.append(
                    makeViolation(
                        "architecture.importDirection",
                        record.path,
                        importRecord.line,
                        f"L{ownerLayer} {record.topPackage} imports L{targetLayer} {target}",
                    )
                )
    return violations


def checkL1CrossImport(records: list[ModuleRecord]) -> list[Violation]:
    """gather/providers module-level cross import 금지."""
    violations: list[Violation] = []
    for record in records:
        if record.topPackage not in L1_PEERS:
            continue
        for importRecord in record.imports:
            if not importRecord.isTopLevel:
                continue
            target = importRecord.topPackage
            if target in L1_PEERS and target != record.topPackage:
                violations.append(
                    makeViolation(
                        "architecture.l1CrossImport",
                        record.path,
                        importRecord.line,
                        f"{record.topPackage} imports {target}",
                    )
                )
    return violations


def checkL15SiblingImport(records: list[ModuleRecord]) -> list[Violation]:
    """scan/frame/synth/reference sibling import 금지. lazy import도 포함한다."""
    violations: list[Violation] = []
    for record in records:
        if record.topPackage not in L15_PEERS:
            continue
        for importRecord in record.imports:
            target = importRecord.topPackage
            if target in L15_PEERS and target != record.topPackage:
                violations.append(
                    makeViolation(
                        "architecture.l15SiblingImport",
                        record.path,
                        importRecord.line,
                        f"{record.topPackage} imports {target}",
                    )
                )
    return violations


def checkLazyBoundaryDebt(records: list[ModuleRecord]) -> list[Violation]:
    """L1 function-local 상위 import debt를 수집한다.

    module-level import 는 기존 architecture rule 이 직접 차단한다. 이 rule 은
    Company facade / legacy accessor 가 function body 안에서 상위 계층을 당겨 쓰는
    경로를 baseline ledger 에 올려 신규 증가를 막는다.
    """
    violations: list[Violation] = []
    for record in records:
        if record.topPackage not in L1_PEERS:
            continue
        for importRecord in record.imports:
            if importRecord.isTopLevel:
                continue
            target = importRecord.topPackage
            if target is None or target in SINK_HELPERS:
                continue
            if target == ROOT_FACADE:
                violations.append(
                    makeViolation(
                        "architecture.lazyRootFacadeImport",
                        record.path,
                        importRecord.line,
                        f"lazy root-facade import: {record.topPackage} imports dartlab",
                        importKind="root-facade",
                    )
                )
                continue
            if target in L1_PEERS and target != record.topPackage:
                violations.append(
                    makeViolation(
                        "architecture.lazyL1CrossImport",
                        record.path,
                        importRecord.line,
                        f"lazy L1 cross import: {record.topPackage} imports {target}",
                        importKind="lazy",
                    )
                )
                continue
            if target in L15_PEERS or target in L2_PEERS:
                violations.append(
                    makeViolation(
                        "architecture.lazyUpperImport",
                        record.path,
                        importRecord.line,
                        f"lazy upper import: {record.topPackage} imports {target}",
                        importKind="lazy",
                    )
                )
    return violations


def makeViolation(rule: str, path: str, line: int, message: str, *, importKind: str = "direct") -> Violation:
    """표준 baseline key를 가진 Violation 생성."""
    baselineKey = f"{rule}:{importKind}:{path}:{line}"
    return Violation(
        rule=rule,
        path=path,
        line=line,
        message=f"[{importKind}] {message}",
        severity="error",
        baselineKey=baselineKey,
    )

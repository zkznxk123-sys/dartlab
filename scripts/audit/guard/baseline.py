"""Guard baseline ledger 비교."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from guard.rules import Violation


@dataclass(frozen=True)
class BaselineResult:
    """baseline 비교 결과."""

    newViolations: tuple[Violation, ...]
    knownViolations: tuple[Violation, ...]
    staleKnown: tuple[str, ...]
    deferred: dict[str, Any]

    def toDict(self) -> dict[str, Any]:
        """JSON 직렬화용 dict."""
        return {
            "newViolations": [item.toDict() for item in self.newViolations],
            "knownViolations": [item.toDict() for item in self.knownViolations],
            "staleKnown": list(self.staleKnown),
            "deferred": self.deferred,
        }


def loadBaseline(path: Path) -> dict[str, Any]:
    """baseline JSON을 읽는다."""
    if not path.exists():
        return {"version": 1, "policy": "no_new_violations", "known": {}, "deferred": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"baseline must be object: {path}")
    if data.get("version") != 1:
        raise ValueError(f"unsupported baseline version: {path}")
    known = data.get("known", {})
    if not isinstance(known, dict):
        raise ValueError(f"baseline known must be object: {path}")
    deferred = data.get("deferred", {})
    if not isinstance(deferred, dict):
        raise ValueError(f"baseline deferred must be object: {path}")
    return data


def compareBaseline(violations: list[Violation], baseline: dict[str, Any]) -> BaselineResult:
    """신규/기존/stale known 위반을 분류한다."""
    knownKeys = flattenKnownKeys(baseline.get("known", {}))
    foundKeys = {item.baselineKey for item in violations}
    knownViolations = tuple(item for item in violations if item.baselineKey in knownKeys)
    newViolations = tuple(item for item in violations if item.baselineKey not in knownKeys)
    staleKnown = tuple(sorted(knownKeys - foundKeys))
    return BaselineResult(
        newViolations=newViolations,
        knownViolations=knownViolations,
        staleKnown=staleKnown,
        deferred=baseline.get("deferred", {}),
    )


def flattenKnownKeys(known: dict[str, Any]) -> set[str]:
    """baseline known 구조를 rule별 list 또는 flat dict 모두 허용한다."""
    keys: set[str] = set()
    for rule, value in known.items():
        if isinstance(value, list):
            keys.update(str(item) for item in value)
        elif isinstance(value, dict):
            keys.update(str(item) for item in value.keys())
        elif value is True:
            keys.add(str(rule))
    return keys


def baselineResultToDict(result: BaselineResult) -> dict[str, Any]:
    """BaselineResult dict 변환."""
    return asdict(result)

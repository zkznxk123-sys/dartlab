"""Raw cross-company parquet scan 패턴 차단 — P-트랙 룰 9 게이트.

`pl.scan_parquet("data/{provider}/docs/*.parquet")` 처럼 다 회사 일괄 lazy scan 패턴은
STATUS_STACK_BUFFER_OVERRUN (Polars query plan 폭발) 사고 원인.

cross-company query 는 `data/{provider}/scan/docsIndex.parquet` 슬림 인덱스 (P3) 경유만.

baseline (`_baselines/rawCrossScan.json`) 외 위반만 fail.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parent.parent
_BASELINE = _REPO / "scripts" / "audit" / "_baselines" / "rawCrossScan.json"

# 차단 패턴: data/{provider}/docs/*.parquet · data/{provider}/finance/*.parquet glob 일괄
_BANNED_PATTERNS = [
    re.compile(r'pl\.scan_parquet\([^)]*"data/[^"]*/(docs|finance)/\*\.parquet"'),
    re.compile(r'pl\.read_parquet\([^)]*"data/[^"]*/(docs|finance)/\*\.parquet"'),
    re.compile(r'glob\.glob\([^)]*"data/[^"]*/(docs|finance)/\*\.parquet"'),
]

_SCAN_ROOTS = ("src/dartlab",)


def _loadBaseline() -> dict:
    if _BASELINE.exists():
        return json.loads(_BASELINE.read_text(encoding="utf-8"))
    return {"violations": [], "_note": "P0.5 baseline"}


def _scanFile(path: Path) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (UnicodeDecodeError, OSError):
        return []
    violations: list[str] = []
    rel = str(path.relative_to(_REPO).as_posix())
    for i, line in enumerate(lines, start=1):
        for pat in _BANNED_PATTERNS:
            if pat.search(line):
                violations.append(f"{rel}:{i}")
                break
    return violations


def _scanAll() -> list[str]:
    all_violations: list[str] = []
    for root in _SCAN_ROOTS:
        for p in (_REPO / root).rglob("*.py"):
            if "__pycache__" in p.parts:
                continue
            all_violations.extend(_scanFile(p))
    return sorted(all_violations)


def test_no_raw_cross_company_scan() -> None:
    """raw cross-company parquet glob 패턴이 dartlab 코드에 없어야 한다.

    P3 에서 docsIndex 빌더 + Scan.docsSections() API 도입 후 strict 전환.
    P0.5 baseline: 현 위반 (있다면) 기록 — 회귀만 차단.
    """
    violations = _scanAll()
    baseline = _loadBaseline()
    allowed = set(baseline.get("violations", []))
    new_violations = set(violations) - allowed
    assert not new_violations, (
        f"Raw cross-company scan 회귀 {len(new_violations)} 건: {sorted(new_violations)[:10]}. "
        f"cross-company 는 data/{{provider}}/scan/docsIndex.parquet 경유 (P3)."
    )

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


def _isLineViolation(line: str) -> bool:
    """line 에 차단 패턴 매칭 여부 — inline annotation 화이트리스트 적용 후 판정.

    M0: ``# polars-streaming-unsupported`` 주석이 같은 줄에 있으면 차단 예외
    (streaming engine 미지원 pivot/window/asof 22 건의 의도된 eager scan).
    """
    if "polars-streaming-unsupported" in line:
        return False
    for pat in _BANNED_PATTERNS:
        if pat.search(line):
            return True
    return False


def _scanFile(path: Path) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (UnicodeDecodeError, OSError):
        return []
    violations: list[str] = []
    rel = str(path.relative_to(_REPO).as_posix())
    for i, line in enumerate(lines, start=1):
        if _isLineViolation(line):
            violations.append(f"{rel}:{i}")
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


def test_inline_annotation_excluded() -> None:
    """``# polars-streaming-unsupported`` 주석 있는 line 은 차단 제외 (M0 화이트리스트).

    streaming engine 미지원 22 건 (pivot/window/asof) 의 의도된 eager scan 을 위한
    명시 마킹. M3 가 22 호출부에 주석 부착.
    """
    # 차단 패턴 단독 → violation
    assert _isLineViolation('lf = pl.scan_parquet("data/dart/docs/*.parquet")')
    # 차단 패턴 + 주석 → 화이트리스트
    assert not _isLineViolation(
        'lf = pl.scan_parquet("data/dart/docs/*.parquet")  # polars-streaming-unsupported: pivot'
    )
    # 주석만 있고 패턴 없음 → violation 아님
    assert not _isLineViolation("# polars-streaming-unsupported: comment only")
    # 일반 line — 둘 다 없음
    assert not _isLineViolation("x = 1")

"""test/prod LOC 비율 측정 audit — 테스트 품질 KPI (T6-5).

전체 + 모듈별 비율을 산출하여 `metrics workflow` (T1-2) 가 시계열로 수집.
1.0.0 게이트 통과 기준: 전체 ≥ 80% (현재 baseline 64.8%, 2026-05-23).

실행::

    uv run python -X utf8 tests/audit/testLocRatio.py
    uv run python -X utf8 tests/audit/testLocRatio.py --json   # JSON 출력 (CI 산출물)
    uv run python -X utf8 tests/audit/testLocRatio.py --strict --threshold 80
                                                              # 임계값 미달 시 exit 2

측정 정의:
    - prod LOC: ``src/dartlab/**/*.py`` 의 non-empty / non-comment 라인 합
    - test LOC: ``tests/**/*.py`` 의 non-empty / non-comment 라인 합
      (단, ``tests/_attempts/`` 인큐베이션 + ``tests/fixtures/`` HF 캐시 제외)
    - 비율: test LOC / prod LOC × 100

종료 코드::

    0 — 비율 ≥ threshold (또는 --strict 없음)
    2 — --strict + 비율 < threshold
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PROD_ROOT = REPO_ROOT / "src" / "dartlab"
TEST_ROOT = REPO_ROOT / "tests"

# 측정 제외 path prefix (tests/ 안)
TEST_SKIP_PREFIXES: tuple[str, ...] = (
    "_attempts",  # 시도 인큐베이션 (CI 게이트 의무 0)
    "fixtures",  # HF dataset 캐시
    "_drafts",  # draft 보관
)


def countMeaningfulLines(filePath: Path) -> int:
    """파일의 의미있는 라인 수 (empty + 순수 주석 제외)."""
    try:
        text = filePath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        count += 1
    return count


def measureModule(root: Path, skipPrefixes: tuple[str, ...] = ()) -> tuple[int, dict[str, int]]:
    """모듈 root 아래 *.py 의 LOC 합 + sub-namespace 별 분포."""
    total = 0
    bySubnamespace: dict[str, int] = {}
    if not root.exists():
        return 0, {}

    for pyFile in root.rglob("*.py"):
        relParts = pyFile.relative_to(root).parts
        # skip prefix 검사 — 첫 폴더 이름이 skip 에 매치
        if relParts and any(relParts[0].startswith(p) for p in skipPrefixes):
            continue
        # __pycache__ 등 보조 폴더 제외
        if any(p.startswith("_") and p != "_init__.py" and p.startswith("__") for p in relParts[:-1]):
            continue

        loc = countMeaningfulLines(pyFile)
        total += loc
        # sub-namespace = root 다음 첫 폴더 또는 root 직속 파일
        subKey = relParts[0] if len(relParts) > 1 else "__root__"
        bySubnamespace[subKey] = bySubnamespace.get(subKey, 0) + loc

    return total, bySubnamespace


def main() -> int:
    parser = argparse.ArgumentParser(description="test/prod LOC 비율 측정 (T6-5)")
    parser.add_argument("--json", action="store_true", help="JSON 출력 (CI 산출물용)")
    parser.add_argument("--strict", action="store_true", help="threshold 미달 시 exit 2")
    parser.add_argument(
        "--threshold",
        type=float,
        default=80.0,
        help="strict 모드 임계값 (기본 80 percent — 1.0.0 게이트)",
    )
    args = parser.parse_args()

    prodTotal, prodSub = measureModule(PROD_ROOT)
    testTotal, testSub = measureModule(TEST_ROOT, skipPrefixes=TEST_SKIP_PREFIXES)

    ratio = (testTotal / prodTotal * 100) if prodTotal > 0 else 0.0

    result = {
        "measuredAt": dt.datetime.now(dt.UTC).isoformat(),
        "prodLoc": prodTotal,
        "testLoc": testTotal,
        "ratio": round(ratio, 2),
        "threshold": args.threshold,
        "prodBySubnamespace": dict(sorted(prodSub.items(), key=lambda x: -x[1])),
        "testBySubnamespace": dict(sorted(testSub.items(), key=lambda x: -x[1])),
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"[testLocRatio] prod LOC = {prodTotal:,}  ({len(prodSub)} sub-namespace)")
        print(f"[testLocRatio] test LOC = {testTotal:,}  ({len(testSub)} sub-namespace)")
        print(f"[testLocRatio] 비율 = {ratio:.2f} percent  (threshold = {args.threshold:.0f} percent)")
        if ratio >= args.threshold:
            print("[testLocRatio] OK — 임계값 통과")
        else:
            gap = args.threshold - ratio
            needed = int((args.threshold / 100) * prodTotal - testTotal)
            print(f"[testLocRatio] UNDER — 임계값 {gap:.2f} percent 부족 (추가 필요 약 {needed:,} LOC)")

    if args.strict and ratio < args.threshold:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

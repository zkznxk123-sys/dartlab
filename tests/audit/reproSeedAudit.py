"""random seed audit — reproducibility (T7-3) 트랙.

dartlab 안 random 호출 위치 grep + 명시 seed fixture 동행 여부 검증.
재현 가능성 (퀀트 factor / hypothesis fixture / scenario 시뮬레이션) 의 기반.

검사 대상 패턴 (AST 기반 정확도 보강은 후속):
    - ``random.<func>(...)``
    - ``np.random.<func>(...)`` / ``numpy.random.<func>(...)``
    - ``polars.*shuffle*`` (`pl.DataFrame.sample(shuffle=True, ...)` 등)
    - ``rng.<func>(...)`` (Generator 인스턴스 호출은 정상 — seed 명시한 객체)

허용 조건:
    - 같은 파일에 ``seed=`` 또는 ``random_state=`` 또는 ``rng = `` 키워드 동행
    - ``tests/`` 안 ``@pytest.fixture`` + seed 인자 동행
    - ``# seed-audit: ok ...`` 주석 명시 (justify)

baseline 부채 원장: ``tests/audit/_baselines/reproSeed.json`` (현재 위반 allowlist).

실행::

    uv run python -X utf8 tests/audit/reproSeedAudit.py
    uv run python -X utf8 tests/audit/reproSeedAudit.py --strict
    uv run python -X utf8 tests/audit/reproSeedAudit.py --update-baseline

종료 코드:
    0 — baseline 변동 없음 또는 --strict 없음
    2 — --strict + 신규 위반 발견 (baseline 초과)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC = REPO_ROOT / "src" / "dartlab"
TESTS = REPO_ROOT / "tests"
BASELINE_FILE = REPO_ROOT / "tests" / "audit" / "_baselines" / "reproSeed.json"

# 위험 패턴 (regex). False-positive 는 베이스라인 또는 # seed-audit: ok 로 우회.
_RISKY_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\brandom\.(random|randint|choice|sample|shuffle|uniform|gauss|expovariate)\(", "stdlib random"),
    (r"\bnp\.random\.(rand|randn|randint|choice|sample|shuffle|seed)\(", "numpy random"),
    (r"\bnumpy\.random\.(rand|randn|randint|choice|sample|shuffle|seed)\(", "numpy random full"),
    (r"\.sample\([^)]*shuffle\s*=\s*True", "polars sample shuffle"),
)

# 허용 신호: 같은 파일에 등장하면 seed 가 명시된 것으로 간주.
_ACCEPT_SIGNALS: tuple[str, ...] = (
    "seed=",
    "random_state=",
    "rng = ",
    "rng=",
    "np.random.default_rng",
    "numpy.random.default_rng",
    "# seed-audit: ok",
)

# 검사 제외 (외부 패키지 wrapper, 시도 인큐베이션 등).
_SKIP_PATH_PREFIXES: tuple[str, ...] = (
    "_attempts",
    "_drafts",
    "__pycache__",
    "fixtures",
)


def _shouldSkip(relPath: Path) -> bool:
    return any(part.startswith(prefix) for part in relPath.parts for prefix in _SKIP_PATH_PREFIXES)


def scanFile(filePath: Path) -> list[tuple[int, str, str]]:
    """파일 안 위험 패턴 line 목록 — (line_no, pattern_name, raw_line)."""
    try:
        text = filePath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    # 같은 파일에 허용 신호 동행 시 전체 skip
    if any(sig in text for sig in _ACCEPT_SIGNALS):
        return []

    hits: list[tuple[int, str, str]] = []
    for lineNo, line in enumerate(text.splitlines(), start=1):
        for pattern, name in _RISKY_PATTERNS:
            if re.search(pattern, line):
                hits.append((lineNo, name, line.strip()))
                break
    return hits


def collectViolations() -> dict[str, list[dict]]:
    """src/dartlab + tests/ 전체 스캔 결과 정렬된 dict."""
    violations: dict[str, list[dict]] = {}
    for root in (SRC, TESTS):
        if not root.exists():
            continue
        for pyFile in root.rglob("*.py"):
            relPath = pyFile.relative_to(REPO_ROOT)
            if _shouldSkip(relPath):
                continue
            hits = scanFile(pyFile)
            if hits:
                violations[str(relPath).replace("\\", "/")] = [
                    {"line": lineNo, "pattern": name, "text": text} for lineNo, name, text in hits
                ]
    return dict(sorted(violations.items()))


def loadBaseline() -> dict[str, list[dict]]:
    if not BASELINE_FILE.exists():
        return {}
    return json.loads(BASELINE_FILE.read_text(encoding="utf-8"))


def saveBaseline(violations: dict[str, list[dict]]) -> None:
    BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_FILE.write_text(
        json.dumps(violations, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="random seed reproducibility audit (T7-3)")
    parser.add_argument("--strict", action="store_true", help="신규 위반 발견 시 exit 2")
    parser.add_argument("--update-baseline", action="store_true", help="현재 위반을 baseline 으로 저장")
    parser.add_argument("--json", action="store_true", help="JSON 출력 (CI 산출물용)")
    args = parser.parse_args()

    current = collectViolations()
    baseline = loadBaseline()

    if args.update_baseline:
        saveBaseline(current)
        print(f"[reproSeed] baseline 갱신 — {len(current)} 파일, {sum(len(v) for v in current.values())} 항목")
        return 0

    if args.json:
        print(
            json.dumps(
                {
                    "current": current,
                    "baseline": baseline,
                    "newViolations": sorted(set(current) - set(baseline)),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    totalFiles = len(current)
    totalHits = sum(len(v) for v in current.values())
    newFiles = sorted(set(current) - set(baseline))

    print(f"[reproSeed] 현재 위반 — {totalFiles} 파일, {totalHits} 항목")
    print(f"[reproSeed] baseline — {len(baseline)} 파일")

    if newFiles:
        print(f"[reproSeed] 신규 위반 (baseline 초과) {len(newFiles)} 파일:")
        for f in newFiles[:20]:
            print(f"  - {f}  ({len(current[f])} 항목)")
        if len(newFiles) > 20:
            print(f"  ... 외 {len(newFiles) - 20} 파일")
    else:
        print("[reproSeed] OK — baseline 변동 없음")

    if args.strict and newFiles:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

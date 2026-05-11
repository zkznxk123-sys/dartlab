"""P-트랙 11 룰 통합 gate — 한 번에 11 audit 실행.

각 audit 의 baseline 대비 결과 집계. 모든 게이트 통과 시 exit 0.

사용법:
    uv run python -X utf8 scripts/audit/providerGate.py
    uv run python -X utf8 scripts/audit/providerGate.py --strict   # baseline 무시
    uv run python -X utf8 scripts/audit/providerGate.py --json     # 결과 JSON 출력
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_REPO = Path(__file__).resolve().parents[2]

_AUDIT_SCRIPTS = [
    ("룰 2 — 폴더 mirror", "scripts/audit/folderMirror.py"),
    ("룰 3 — LoC 임계", "scripts/audit/folderSize.py"),
    ("룰 4 — __init__ thin", "scripts/audit/initThin.py"),
    ("룰 5 — _*.py 0", "scripts/audit/underscoreModules.py"),
    ("룰 6 — docstring 4-섹션", "scripts/audit/docstring4Section.py"),
    ("룰 8 — limit keyword", "scripts/audit/limitDefault.py"),
]

_TEST_GATES = [
    ("룰 1 — Protocol contract", "tests/test_providerContract.py"),
    ("룰 7 — src↔tests mirror", "tests/test_structureMirror.py"),
    ("룰 9 — raw cross-scan", "tests/test_no_raw_cross_scan.py"),
    ("룰 10 — iter pairs", "tests/test_provider_iter_pairs.py"),
    ("룰 11 — Company context", "tests/test_company_context.py"),
]


def _runAudit(scriptPath: str, strict: bool) -> tuple[bool, str]:
    cmd = [sys.executable, "-X", "utf8", scriptPath]
    if strict:
        cmd.append("--strict")
    result = subprocess.run(cmd, cwd=_REPO, capture_output=True, text=True, encoding="utf-8")
    return result.returncode == 0, result.stdout + result.stderr


def _runTest(testPath: str) -> tuple[bool, str]:
    cmd = [sys.executable, "-X", "utf8", "-m", "pytest", testPath, "-v", "--tb=short"]
    result = subprocess.run(cmd, cwd=_REPO, capture_output=True, text=True, encoding="utf-8")
    return result.returncode == 0, result.stdout + result.stderr


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="모든 audit --strict")
    parser.add_argument("--json", action="store_true", help="JSON 결과 출력")
    args = parser.parse_args()

    results: list[dict] = []

    print("=== P-트랙 11 룰 게이트 (providers/) ===\n")

    for label, script in _AUDIT_SCRIPTS:
        passed, output = _runAudit(script, args.strict)
        results.append({"rule": label, "type": "audit", "script": script, "passed": passed})
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {label}")
        if not passed and not args.json:
            print("    " + output.split("\n")[-3] if output else "    (no output)")

    for label, test in _TEST_GATES:
        passed, output = _runTest(test)
        results.append({"rule": label, "type": "test", "script": test, "passed": passed})
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {label}")

    failed = sum(1 for r in results if not r["passed"])
    total = len(results)

    print(f"\n=== {total - failed} / {total} 통과 ===")

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

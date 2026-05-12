"""G-트랙 게이트 — gather/ 도메인 7 룰 통합 audit.

`providerGate.py` 의 자매 script. providers/ 의 11 룰 중 gather/ 에 적용
가능한 7 룰만 일괄 실행. 각 audit script 에 `--baseline <path>` 옵션으로
gather 전용 baseline 을 주입.

적용 룰:
    3. LoC 임계      (folderSize.py + gatherSize.json)
    4. __init__ thin (initThin.py + gatherInit.json)
    5. _*.py 0       (underscoreModules.py + gatherUnderscore.json)
    6. docstring 4-섹션 (docstring4Section.py + gatherDocstring4Section.json)
    8. limit keyword (limitDefault.py + gatherLimitDefault.json)
    7. src↔tests mirror (test_structureMirror.py — gather scope, P-G7 이후)
    9. raw cross-scan (test_no_raw_cross_scan.py — gather scope, P-G8 이후)

제외 룰 (gather 본질 상 적용 불가):
    1 Protocol contract / 2 폴더 mirror / 10 iter pair / 11 Company context

사용법:
    uv run python -X utf8 scripts/audit/gatherGate.py
    uv run python -X utf8 scripts/audit/gatherGate.py --strict   # baseline 무시
    uv run python -X utf8 scripts/audit/gatherGate.py --json     # 결과 JSON 출력
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
_TARGET = "src/dartlab/gather"

# (label, script_path, baseline_path) 3-tuple.
_AUDIT_SCRIPTS = [
    ("룰 3 — LoC 임계", "scripts/audit/folderSize.py", "scripts/audit/_baselines/gatherSize.json"),
    ("룰 4 — __init__ thin", "scripts/audit/initThin.py", "scripts/audit/_baselines/gatherInit.json"),
    ("룰 5 — _*.py 0", "scripts/audit/underscoreModules.py", "scripts/audit/_baselines/gatherUnderscore.json"),
    (
        "룰 6 — docstring 4-섹션",
        "scripts/audit/docstring4Section.py",
        "scripts/audit/_baselines/gatherDocstring4Section.json",
    ),
    ("룰 8 — limit keyword", "scripts/audit/limitDefault.py", "scripts/audit/_baselines/gatherLimitDefault.json"),
]

# 룰 7 (src↔tests mirror) / 룰 9 (raw cross-scan) — pytest 기반 gate.
# test_structureMirror.py 가 gather scope 함수 (test_gather_have_test_mirrors) 보유.
# test_no_raw_cross_scan.py 가 gather scope 함수 (test_gather_no_raw_cross_company_scan) 보유.
_TEST_GATES: list[tuple[str, str]] = [
    ("룰 7 — src↔tests mirror (gather scope)", "tests/test_structureMirror.py::test_gather_have_test_mirrors"),
    ("룰 9 — raw cross-scan (gather scope)", "tests/test_no_raw_cross_scan.py::test_gather_no_raw_cross_company_scan"),
]


def _runAudit(scriptPath: str, baselinePath: str, strict: bool) -> tuple[bool, str]:
    cmd = [sys.executable, "-X", "utf8", scriptPath, _TARGET, "--baseline", baselinePath]
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

    print("=== G-트랙 7 룰 게이트 (gather/) ===\n")

    for label, script, baseline in _AUDIT_SCRIPTS:
        passed, output = _runAudit(script, baseline, args.strict)
        results.append({"rule": label, "type": "audit", "script": script, "passed": passed})
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {label}")
        if not passed and not args.json:
            tail = output.split("\n")[-3] if output else ""
            print(f"    {tail}")

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

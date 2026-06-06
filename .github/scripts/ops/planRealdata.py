"""git diff → realData 테스트 파일 스마트 선택.

PR/push 마다 20개 realData 파일 전수 실행 (60분) 대신, 변경된 소스 경로에
영향받는 엔진 테스트만 골라 matrix 로 돌린다.

매핑 규칙 (우선순위 순):
1. **infra trigger** — core / providers / workflow / pyproject / conftest 변경
   → 전수 (mapping 우회, 모든 파일 반환)
2. **엔진 매핑** — engine src path → 해당 test 파일 + cross-cutting
3. **test 수정** — 수정된 test 파일 본인만 + dependency

Exit:
    stdout 에 JSON array (test 파일 이름 목록). 빈 배열이면 skip 신호.

Usage (CI):
    python planRealdata.py
    # → ["test_analysis.py", "test_analysisAxes.py", "test_topLevelApi.py"]
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

# ── 모든 realData 테스트 파일 ────────────────────────────────────
ALL_TESTS: list[str] = [
    "test_ai.py",
    "test_analysis.py",
    "test_analysisAxes.py",
    "test_companyExhaustive.py",
    "test_companyFacade.py",
    "test_companyTopics.py",
    "test_credit.py",
    "test_creditAxes.py",
    "test_freshInstall.py",
    "test_gather.py",
    "test_gatherAxes.py",
    "test_industry.py",
    "test_macro.py",
    "test_macroAxes.py",
    "test_quant.py",
    "test_story.py",
    "test_scan.py",
    "test_scanAxes.py",
    "test_search.py",
    "test_topLevelApi.py",
]

# ── infra 경로 — 하나라도 변경되면 전수 실행 ─────────────────────
INFRA_PREFIXES: tuple[str, ...] = (
    "src/dartlab/core/",
    "src/dartlab/providers/",  # DART/EDGAR L1 — 모든 엔진의 기반
    "src/dartlab/__init__.py",
    "pyproject.toml",
    ".github/workflows/ci.yml",
    ".github/workflows/ci-fast.yml",
    ".github/workflows/ci-full.yml",
    ".github/workflows/ci-nightly.yml",
    ".github/workflows/publish.yml",
    ".github/scripts/ops/planRealdata.py",
    ".github/scripts/ops/prepareRealdataScanCache.py",
    "tests/audit/publicApiScenarios.yml",
    "tests/audit/productSmoke.py",
    "tests/audit/publicApiCoverage.py",
    "tests/audit/memoryBudgetAudit.py",
    "tests/audit/resourceBudgets.json",
    "tests/test-realdata.sh",
    "tests/test-lock.sh",
    "tests/realData/conftest.py",
    "tests/realData/__init__.py",
)

# ── 엔진 경로 → 테스트 파일 매핑 ─────────────────────────────────
ENGINE_MAP: dict[str, list[str]] = {
    "src/dartlab/analysis/": ["test_analysis.py", "test_analysisAxes.py"],
    "src/dartlab/credit/": ["test_credit.py", "test_creditAxes.py"],
    "src/dartlab/macro/": ["test_macro.py", "test_macroAxes.py"],
    "src/dartlab/scan/": ["test_scan.py", "test_scanAxes.py"],
    "src/dartlab/gather/": ["test_gather.py", "test_gatherAxes.py"],
    "src/dartlab/quant/": ["test_quant.py"],
    "src/dartlab/story/": ["test_story.py"],
    "src/dartlab/industry/": ["test_industry.py"],
    "src/dartlab/search/": ["test_search.py"],
    "src/dartlab/ai/": ["test_ai.py"],
    "src/dartlab/display/": ["test_topLevelApi.py"],
    "src/dartlab/viz/": ["test_topLevelApi.py"],
}

# Company facade 는 analysis/gather 등 여러 엔진을 엮어 부르므로 facade 테스트는
# 해당 엔진 변경 시에도 함께 돌린다. 매 엔진 변경에 자동 포함.
COMPANY_FACADE_TESTS: list[str] = [
    "test_companyFacade.py",
    "test_companyTopics.py",
    "test_companyExhaustive.py",
    "test_topLevelApi.py",
]


def getChangedFiles() -> list[str]:
    """HEAD 직전 커밋 대비 수정된 파일 목록."""
    # CI 환경에서 base ref 추정
    base = os.environ.get("GITHUB_BASE_REF") or os.environ.get("BASE_REF") or "HEAD~1"
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{base}...HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    # fallback: HEAD~1..HEAD (PR 아닌 push 의 경우)
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    return []


def planTests(changedFiles: list[str]) -> list[str]:
    """변경 파일 → 실행할 test 파일 목록 (sorted unique).

    Returns
    -------
    list[str]
        실행 대상 test 파일 이름 (tests/realData/ 아래). 전수 실행이면 ALL_TESTS.
    """
    if not changedFiles:
        # diff 추출 실패 또는 변경 없음 → 안전하게 전수
        return list(ALL_TESTS)

    # infra 변경 → 전수
    for f in changedFiles:
        norm = f.replace("\\", "/")
        if any(norm.startswith(p) for p in INFRA_PREFIXES):
            return list(ALL_TESTS)

    selected: set[str] = set()
    hasEngineChange = False

    for f in changedFiles:
        norm = f.replace("\\", "/")
        # 엔진 매핑 적중
        for prefix, tests in ENGINE_MAP.items():
            if norm.startswith(prefix):
                selected.update(tests)
                hasEngineChange = True
                break

        # tests/realData/test_*.py 직접 수정 → 본인 포함
        if norm.startswith("tests/realData/test_") and norm.endswith(".py"):
            fname = Path(norm).name
            if fname in ALL_TESTS:
                selected.add(fname)

    # 엔진 코드가 하나라도 변했다면 company facade smoke 도 함께
    if hasEngineChange:
        selected.update(COMPANY_FACADE_TESTS)

    return sorted(selected & set(ALL_TESTS))


def main() -> int:
    changed = getChangedFiles()
    tests = planTests(changed)
    # stderr 에 진단 정보 (로그 가시용)
    print(f"[planRealdata] changed files: {len(changed)}", file=sys.stderr)
    for f in changed[:10]:
        print(f"  - {f}", file=sys.stderr)
    if len(changed) > 10:
        print(f"  ... and {len(changed) - 10} more", file=sys.stderr)
    print(f"[planRealdata] selected tests: {len(tests)}/{len(ALL_TESTS)}", file=sys.stderr)
    for t in tests:
        print(f"  > {t}", file=sys.stderr)

    print(json.dumps(tests))
    return 0


if __name__ == "__main__":
    sys.exit(main())

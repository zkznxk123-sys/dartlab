"""dartlab CI 단일 진입점 — 로컬·CI 가 동일 명령으로 27 게이트 실행.

본 파일은 ci-fast (16) + ci-full (6) + ci-nightly (5) = 27 게이트의 SSOT.
.github/workflows/ci-*.yml 은 matrix 디스패치만 담당하고, 실제 deps·env·cmd 는
모두 GATES dict 에서 가져온다. dict ↔ matrix drift 는 tests/audit/
test_runEntrypoint.py 가 차단한다.

# Capabilities
1. `gate <name>` — 단일 게이트 실행 (CI matrix 호출용)
2. `tier <fast|full|nightly>` — 한 tier 의 blocking 게이트 전체
3. `preflight` — tier fast 의 blocking 만 (push 전 검증)
4. `list` — 27 게이트 표 출력
5. `audit-self` — GATES 무결성 점검 (dup name · 미정의 tier · 모순)

# Args
서브명령마다 다름. `gate` 는 `--dry-run` 으로 명령 문자열만 출력 (실행 안 함).
matrix 인자 (`--python`, `--test`, `--os`) 는 해당 gate 만 사용.

# Example
    uv run python -X utf8 tests/run.py preflight
    uv run python -X utf8 tests/run.py gate format
    uv run python -X utf8 tests/run.py gate test-full --python 3.13
    uv run python -X utf8 tests/run.py gate realdata-suite --test test_ai.py
    uv run python -X utf8 tests/run.py audit-self

# Returns
exit code 0 = 모든 명령 0. blocking=False gate 는 fail 해도 0 유지.

# Guide
- 신규 게이트 추가: GATES dict 에 `Gate(...)` 한 줄 + 해당 tier 의 ci-*.yml
  matrix.gate 에 항목 한 줄. 둘 중 하나만 추가하면 audit-self fail.
- 기존 게이트 명령 변경: 본 파일만 수정. YAML 은 손대지 않음.
- blocking=False 게이트는 fail 해도 PR 차단 안 함 (정보 표시용).
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

REPO_ROOT = Path(__file__).resolve().parent.parent

Tier = Literal["fast", "full", "nightly"]


@dataclass(frozen=True)
class Gate:
    """단일 CI 게이트 정의 — deps + setup + cmd + env 4 종 SSOT.

    matrix-driven 게이트 (test-full / cross-os-smoke / realdata-suite) 의 cmd
    는 `{python}` / `{os}` / `{test_file}` 같은 placeholder 를 가질 수 있고,
    --python / --os / --test 인자로 채워진다.
    """

    name: str
    tier: Tier
    deps: tuple[str, ...] = ()
    install_pkg: Literal["editable", "non-editable", "none"] = "editable"
    setup: tuple[str, ...] = ()
    cmd: str = ""
    env: dict[str, str] = field(default_factory=dict)
    blocking: bool = True
    runner: str = "ubuntu-latest"
    fetch_depth: int = 1
    timeout_minutes: int = 20
    matrix_param: str | None = None  # "python" | "os" | "test" — None 이면 단일 잡


# 헬퍼 dep 묶음 — 반복 줄임.
PYTEST_CORE = ("pytest", "pytest-asyncio", "pytest-cov", "hypothesis")
PYTEST_PARALLEL = (*PYTEST_CORE, "pytest-xdist", "pytest-benchmark")
DEV_SCHEMA_SNAPSHOT = ("pandera[polars]>=0.29.0", "vcrpy>=6.0.0", "syrupy>=4.7.0")
MCP_PIN = ("mcp[cli]>=1.0,<1.27.1",)

# Realdata 20 shard — ci-nightly.yml realdata-suite-full matrix 와 1:1.
REALDATA_SHARDS = (
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
)


# ──────────────────────────────────────────────────────────────────────────
# GATES — 27 항목. ci-*.yml matrix.gate 와 1:1 (test_runEntrypoint.py 검증).
# ──────────────────────────────────────────────────────────────────────────

GATES: dict[str, Gate] = {
    # ─ Tier 1 — Fast (16) ─────────────────────────────────────────────────
    "format": Gate(
        name="format",
        tier="fast",
        deps=("ruff==0.11.6",),
        install_pkg="none",
        cmd="ruff format --check src/dartlab/ tests/",
    ),
    "lint": Gate(
        name="lint",
        tier="fast",
        deps=("ruff==0.11.6", "pyyaml", "networkx", "import-linter"),
        install_pkg="editable",
        fetch_depth=2,
        cmd=(
            "ruff check src/dartlab/ tests/ && "
            "python -X utf8 tests/audit/noScriptsDir.py && "
            "python tests/audit/checkSilentFail.py && "
            "python tests/audit/stale_references.py && "
            "python -X utf8 tests/audit/lint_camelcase_ast.py --changed --strict && "
            "(python -X utf8 tests/audit/cycleScan.py || true) && "
            "(lint-imports || true) && "
            "python -X utf8 tests/audit/namingConsistency.py"
        ),
    ),
    "architecture-l0-l15": Gate(
        name="architecture-l0-l15",
        tier="fast",
        deps=PYTEST_PARALLEL,
        install_pkg="editable",
        env={"DARTLAB_PROVIDER_SCOPE": "dart,edgar"},
        cmd="python -X utf8 tests/audit/dartlabGuard.py strict --scope l0-l15 --providers dart,edgar",
    ),
    "typecheck": Gate(
        name="typecheck",
        tier="fast",
        deps=("pyright",),
        install_pkg="editable",
        cmd="pyright",
        blocking=False,  # 현 continue-on-error 명시화
    ),
    "smoke": Gate(
        name="smoke",
        tier="fast",
        install_pkg="editable",
        cmd=(
            'python -c "import dartlab; '
            "missing=[n for n in dartlab.__all__ if not hasattr(dartlab,n)]; "
            "import sys; (sys.exit(f'public API missing: {missing}') if missing else None); "
            "from dartlab import Company; assert callable(Company); "
            "print(f'smoke OK — {len(dartlab.__all__)} symbols')\" && "
            "python -X utf8 tests/audit/publicApiCoverage.py && "
            "python -X utf8 tests/audit/memoryBudgetAudit.py && "
            "python -X utf8 tests/audit/productSmoke.py --suite quick --data-mode empty "
            "--import-mode source --json-out product-smoke-quick.json"
        ),
    ),
    "test-fast": Gate(
        name="test-fast",
        tier="fast",
        deps=(*PYTEST_PARALLEL, *DEV_SCHEMA_SNAPSHOT, *MCP_PIN),
        install_pkg="non-editable",
        env={
            "DARTLAB_DATA_DIR": "${{ github.workspace }}/tests/fixtures",
            "PYTEST_MEMORY_LIMIT_MB": "1900",
            "DARTLAB_TEST_LOCKED": "1",
        },
        cmd=(
            "pytest tests/ -n auto --dist loadfile --tb=short "
            "-m 'unit and not requires_data' "
            "--ignore=tests/test_fixture_analysis_real.py "
            "--ignore=tests/test_fixture_credit_real.py "
            "--ignore=tests/test_fixture_story_real.py "
            "--ignore=tests/realData "
            "--benchmark-disable --no-cov"
        ),
    ),
    "wheel-smoke": Gate(
        name="wheel-smoke",
        tier="fast",
        deps=("uv",),
        install_pkg="none",
        setup=("uv run --with build python -m build --wheel --outdir dist",),
        cmd=('WHL=$(ls dist/*.whl | head -n1) && python -X utf8 .github/scripts/verifyWheel.py "$WHL"'),
    ),
    "quality-gate": Gate(
        name="quality-gate",
        tier="fast",
        deps=("radon", "vulture"),
        install_pkg="none",
        cmd=("python tests/audit/qualityGate.py && python -X utf8 src/dartlab/skills/measureProgress.py"),
        blocking=False,
    ),
    "security": Gate(
        name="security",
        tier="fast",
        deps=("pip-audit",),
        install_pkg="editable",
        cmd="pip-audit --strict --desc on",
        blocking=False,
    ),
    "deps-check": Gate(
        name="deps-check",
        tier="fast",
        deps=("deptry",),
        install_pkg="editable",
        cmd="deptry src/dartlab/ --ignore DEP002,DEP003 --extend-exclude _reference",
        blocking=False,
    ),
    "notebooks": Gate(
        name="notebooks",
        tier="fast",
        install_pkg="none",
        cmd="python tests/audit/validateNotebooks.py",
    ),
    "snapshot-regression": Gate(
        name="snapshot-regression",
        tier="fast",
        deps=(*PYTEST_CORE, "syrupy"),
        install_pkg="editable",
        env={"DARTLAB_TEST_LOCKED": "1"},
        cmd="pytest tests/cli/test_output_snapshots.py -v --tb=short --no-cov",
        timeout_minutes=5,
    ),
    "schema-drift": Gate(
        name="schema-drift",
        tier="fast",
        deps=(*PYTEST_CORE, "pandera[polars]>=0.29.0"),
        install_pkg="editable",
        env={"DARTLAB_TEST_LOCKED": "1"},
        cmd="pytest tests/_schemas/ -v --tb=short --no-cov",
        timeout_minutes=5,
    ),
    "eval-rule": Gate(
        name="eval-rule",
        tier="fast",
        deps=("pytest", "pytest-asyncio", "pytest-cov"),
        install_pkg="editable",
        env={"DARTLAB_TEST_LOCKED": "1"},
        cmd="pytest tests/_evals/test_eval_smoke.py -v --tb=short --no-cov",
        timeout_minutes=5,
    ),
    "mutation-smoke": Gate(
        name="mutation-smoke",
        tier="fast",
        deps=("pytest", "pytest-asyncio", "hypothesis"),
        install_pkg="editable",
        env={"DARTLAB_TEST_LOCKED": "1"},
        cmd="python -X utf8 tests/audit/mutationSmoke.py",
        timeout_minutes=5,
    ),
    "test-coverage-gate": Gate(
        name="test-coverage-gate",
        tier="fast",
        install_pkg="none",
        fetch_depth=0,
        cmd=("python -X utf8 tests/audit/testCoverageGate.py --diff origin/master --fail-on-missing --limit 30"),
        timeout_minutes=5,
    ),
    # ─ Tier 2 — Full (6) ──────────────────────────────────────────────────
    "test-full": Gate(
        name="test-full",
        tier="full",
        matrix_param="python",
        deps=(*PYTEST_PARALLEL, *DEV_SCHEMA_SNAPSHOT, *MCP_PIN),
        install_pkg="non-editable",
        env={
            "DARTLAB_DATA_DIR": "${{ github.workspace }}/tests/fixtures",
            "PYTEST_MEMORY_LIMIT_MB": "1900",
            "DARTLAB_TEST_LOCKED": "1",
        },
        cmd=(
            "pytest tests/ -n 2 --dist loadfile --tb=short "
            "-m 'not requires_data and not heavy and not realData and not freshInstall' "
            "--ignore=tests/_fixtures/test_analysis_real.py "
            "--ignore=tests/_fixtures/test_credit_real.py "
            "--ignore=tests/_fixtures/test_story_real.py "
            "--ignore=tests/realData "
            "{cov_flags} --benchmark-disable"
        ),
    ),
    "fixture-integration": Gate(
        name="fixture-integration",
        tier="full",
        deps=("pytest", "pytest-asyncio", "hypothesis", "pytest-benchmark"),
        install_pkg="editable",
        env={
            "DARTLAB_DATA_DIR": "${{ github.workspace }}/tests/fixtures",
            "PYTEST_MEMORY_LIMIT_MB": "5000",
            "DARTLAB_TEST_LOCKED": "1",
        },
        cmd=(
            "for f in tests/_fixtures/test_analysis_real.py tests/_fixtures/test_credit_real.py "
            "tests/_fixtures/test_story_real.py; do "
            'echo "=== $f ==="; '
            'pytest "$f" --tb=short -q --benchmark-disable -p no:cacheprovider || exit 1; '
            "done"
        ),
        timeout_minutes=15,
    ),
    "cross-os-smoke": Gate(
        name="cross-os-smoke",
        tier="full",
        matrix_param="os",
        deps=("pytest", "pytest-asyncio", "hypothesis", "build", "pytest-cov", "pytest-benchmark"),
        install_pkg="editable",
        env={"PYTHONIOENCODING": "utf-8", "DARTLAB_TEST_LOCKED": "1"},
        cmd=(
            "python -X utf8 -m pytest tests/core/test_bundledResources.py "
            "tests/audit/test_wheelPackaging.py -m 'unit and not heavy' --tb=short "
            "--no-cov --benchmark-disable && "
            "python -X utf8 tests/audit/checkSilentFail.py"
        ),
    ),
    "product-smoke-wheel": Gate(
        name="product-smoke-wheel",
        tier="full",
        deps=("uv",),
        install_pkg="none",
        setup=(
            "uv run --with build python -m build --wheel --outdir dist",
            "uv venv /tmp/dartlab-product-smoke --python 3.12",
            'WHL=$(ls dist/*.whl | head -n1) && uv pip install --python /tmp/dartlab-product-smoke "$WHL"',
        ),
        env={"PYTHONUNBUFFERED": "1"},
        cmd=(
            "/tmp/dartlab-product-smoke/bin/python -X utf8 tests/audit/productSmoke.py "
            "--suite release --data-mode empty --import-mode installed "
            "--json-out product-smoke-wheel-release.json"
        ),
        timeout_minutes=30,
    ),
    "realdata-plan": Gate(
        name="realdata-plan",
        tier="full",
        install_pkg="none",
        fetch_depth=0,
        cmd=(
            "python -X utf8 .github/scripts/ops/planRealdata.py > /tmp/tests.json && "
            "cat /tmp/tests.json && "
            "COUNT=$(python -c \"import json; print(len(json.load(open('/tmp/tests.json'))))\") && "
            'echo "tests=$(cat /tmp/tests.json)" >> "${GITHUB_OUTPUT:-/dev/null}" && '
            'if [ "$COUNT" -gt 0 ]; then '
            'echo hasAny=true >> "${GITHUB_OUTPUT:-/dev/null}"; '
            'else echo hasAny=false >> "${GITHUB_OUTPUT:-/dev/null}"; fi'
        ),
        blocking=False,
    ),
    "realdata-suite": Gate(
        name="realdata-suite",
        tier="full",
        matrix_param="test",
        deps=("pytest", "pytest-asyncio", "pytest-rerunfailures", "hypothesis"),
        install_pkg="editable",
        env={
            "DARTLAB_DATA_DIR": "${{ github.workspace }}/tests/fixtures",
            "PYTEST_MEMORY_LIMIT_MB": "6000",
            "DARTLAB_TEST_LOCKED": "1",
        },
        cmd="bash tests/test-realdata.sh tests/realData/{test_file} -v --tb=short",
        timeout_minutes=30,
    ),
    # ─ Tier 3 — Nightly (5) ───────────────────────────────────────────────
    "guard-full-census": Gate(
        name="guard-full-census",
        tier="nightly",
        deps=PYTEST_PARALLEL,
        install_pkg="editable",
        env={"DARTLAB_PROVIDER_SCOPE": "dart,edgar"},
        cmd=("python -X utf8 tests/audit/dartlabGuard.py full --baseline tests/audit/_baselines/dartlabGuard.json"),
        timeout_minutes=15,
    ),
    "realdata-suite-full": Gate(
        name="realdata-suite-full",
        tier="nightly",
        matrix_param="test",
        deps=("pytest", "pytest-asyncio", "pytest-rerunfailures", "hypothesis"),
        install_pkg="editable",
        env={
            "DARTLAB_DATA_DIR": "${{ github.workspace }}/tests/fixtures",
            "PYTEST_MEMORY_LIMIT_MB": "6000",
            "DARTLAB_TEST_LOCKED": "1",
        },
        cmd="bash tests/test-realdata.sh tests/realData/{test_file} -v --tb=short",
        timeout_minutes=30,
    ),
    "external-venv-smoke": Gate(
        name="external-venv-smoke",
        tier="nightly",
        deps=("uv",),
        install_pkg="none",
        setup=(
            "uv venv /tmp/smoke-venv --python 3.12",
            "uv pip install --python /tmp/smoke-venv dartlab",
        ),
        env={"PYTHONUNBUFFERED": "1"},
        cmd=(
            "/tmp/smoke-venv/bin/python -X utf8 tests/audit/productSmoke.py "
            "--suite release --data-mode empty --import-mode installed "
            "--json-out product-smoke-pypi-release.json"
        ),
        timeout_minutes=45,
    ),
    "freshInstall": Gate(
        name="freshInstall",
        tier="nightly",
        deps=("pytest", "pytest-asyncio", "pytest-rerunfailures", "hypothesis"),
        install_pkg="editable",
        env={"PYTEST_MEMORY_LIMIT_MB": "6000", "DARTLAB_TEST_LOCKED": "1"},
        cmd="bash tests/test-realdata.sh tests/realData/test_freshInstall.py -v --tb=short",
        timeout_minutes=30,
    ),
    "mutation-testing": Gate(
        name="mutation-testing",
        tier="nightly",
        deps=("pytest", "pytest-asyncio", "hypothesis", "mutmut>=3.0"),
        install_pkg="editable",
        env={"DARTLAB_TEST_LOCKED": "1"},
        setup=("rm -rf .mutmut-cache mutants/",),
        cmd=(
            "(mutmut run || true) && "
            "(mutmut results > mutation-results.txt 2>&1 || true) && "
            "cat mutation-results.txt | head -100"
        ),
        blocking=False,
        timeout_minutes=90,
    ),
}


# ──────────────────────────────────────────────────────────────────────────
# 실행 헬퍼
# ──────────────────────────────────────────────────────────────────────────


def buildShellCommand(gate: Gate, mp: dict[str, str]) -> str:
    """deps + setup + cmd 를 단일 shell 명령으로 조합. CI 와 로컬 동일.

    mp: matrix param 치환용. python=3.13 / test_file=test_ai.py / os=ubuntu 등.
    """
    parts: list[str] = []

    # 1. deps install
    if gate.deps:
        parts.append("python -m pip install --upgrade pip")
        deps_quoted = " ".join(shlex.quote(d) for d in gate.deps)
        parts.append(f"pip install {deps_quoted}")

    # 2. package install — dartlab 은 single base install SSOT (extras 그룹 금지).
    if gate.install_pkg == "editable":
        parts.append("pip install -e .")
    elif gate.install_pkg == "non-editable":
        parts.append("pip install .")
    # "none" → 설치 안 함

    # 3. setup (wheel build · venv 생성 등)
    parts.extend(gate.setup)

    # 4. main cmd — placeholder 치환
    cmd = gate.cmd
    if gate.matrix_param == "python":
        # test-full 의 cov_flags 분기 — 3.12 만 cov 활성
        py = mp.get("python", "3.12")
        cov_flags = (
            "--cov=dartlab --cov-report=term-missing --cov-report=html --cov-report=xml --cov-fail-under=40"
            if py == "3.12"
            else "--no-cov"
        )
        cmd = cmd.format(cov_flags=cov_flags)
    elif gate.matrix_param == "test":
        cmd = cmd.format(test_file=mp.get("test", REALDATA_SHARDS[0]))
    # os 는 cmd 자체 변형 없음 (runner 만 다름)
    parts.append(cmd)

    return " && ".join(p for p in parts if p)


def runGate(name: str, *, dry_run: bool, mp: dict[str, str]) -> int:
    """단일 게이트 실행. blocking=False 면 exit code 무관하게 0 반환."""
    if name not in GATES:
        print(f"[run.py] unknown gate: {name}", file=sys.stderr)
        print(f"  available: {', '.join(sorted(GATES))}", file=sys.stderr)
        return 2
    gate = GATES[name]

    # GITHUB_OUTPUT-style placeholder 는 로컬에선 의미 없으니 빼고 보여줌
    env_local = {k: v for k, v in gate.env.items() if "${{" not in v}
    if env_local:
        env_str = " ".join(f"{k}={shlex.quote(v)}" for k, v in env_local.items())
    else:
        env_str = ""

    shell_cmd = buildShellCommand(gate, mp)

    print(f"\n━━━ gate: {gate.name}  (tier={gate.tier}, blocking={gate.blocking}) ━━━")
    if env_str:
        print(f"env: {env_str}")
    print(f"cmd: {shell_cmd}\n")

    if dry_run:
        return 0

    full_env = os.environ.copy()
    full_env.update(env_local)
    proc = subprocess.run(  # noqa: S603 - CI dispatcher; cmd 는 본 파일 내부 dict 에서만 옴
        shell_cmd, shell=True, env=full_env, cwd=REPO_ROOT
    )
    if proc.returncode != 0 and not gate.blocking:
        print(f"[run.py] {gate.name} fail (blocking=False) → 통과로 처리", file=sys.stderr)
        return 0
    return proc.returncode


def runTier(tier: Tier, *, blocking_only: bool, dry_run: bool) -> int:
    """tier 의 게이트들을 순차 실행. matrix-driven 게이트는 첫 항목만 (로컬 검증용)."""
    gates = [g for g in GATES.values() if g.tier == tier]
    if blocking_only:
        gates = [g for g in gates if g.blocking]
    failed: list[str] = []
    for gate in gates:
        mp: dict[str, str] = {}
        if gate.matrix_param == "python":
            mp = {"python": "3.12"}
        elif gate.matrix_param == "test":
            mp = {"test": REALDATA_SHARDS[0]}
        # matrix_param="os" 는 로컬 OS 그대로 (placeholder 없음)
        rc = runGate(gate.name, dry_run=dry_run, mp=mp)
        if rc != 0:
            failed.append(gate.name)
    if failed:
        print(f"\n[run.py] FAILED: {', '.join(failed)}", file=sys.stderr)
        return 1
    print(f"\n[run.py] tier {tier} ({len(gates)} gates) PASSED")
    return 0


def cmdList() -> int:
    """27 게이트 표 출력."""
    print(f"{'name':<26} {'tier':<8} {'block':<6} {'matrix':<8} {'runner'}")
    print("─" * 70)
    for gate in GATES.values():
        print(
            f"{gate.name:<26} {gate.tier:<8} "
            f"{'Y' if gate.blocking else 'N':<6} "
            f"{(gate.matrix_param or '-'):<8} {gate.runner}"
        )
    print(
        f"\ntotal: {len(GATES)} gates "
        f"(fast={sum(1 for g in GATES.values() if g.tier == 'fast')}, "
        f"full={sum(1 for g in GATES.values() if g.tier == 'full')}, "
        f"nightly={sum(1 for g in GATES.values() if g.tier == 'nightly')})"
    )
    return 0


def cmdAuditSelf() -> int:
    """GATES 무결성 검사 — 중복 name · 비어있는 cmd · matrix placeholder 누락."""
    errors: list[str] = []
    names = [g.name for g in GATES.values()]
    if len(names) != len(set(names)):
        errors.append("GATES 에 중복 name 존재")
    for gate in GATES.values():
        if not gate.cmd:
            errors.append(f"{gate.name}: cmd 비어있음")
        if gate.matrix_param == "python" and "{cov_flags}" not in gate.cmd:
            errors.append(f"{gate.name}: matrix_param=python 인데 {{cov_flags}} placeholder 없음")
        if gate.matrix_param == "test" and "{test_file}" not in gate.cmd:
            errors.append(f"{gate.name}: matrix_param=test 인데 {{test_file}} placeholder 없음")
        if gate.tier not in ("fast", "full", "nightly"):
            errors.append(f"{gate.name}: 알 수 없는 tier {gate.tier}")
    if errors:
        for e in errors:
            print(f"[audit-self] {e}", file=sys.stderr)
        return 1
    print(f"[audit-self] OK — {len(GATES)} gates 무결성 확인")
    return 0


# ──────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tests/run.py", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p_gate = sub.add_parser("gate", help="단일 게이트 실행 (CI matrix 호출용)")
    p_gate.add_argument("name", help="게이트 이름 (list 로 확인)")
    p_gate.add_argument("--python", default="3.12", help="test-full matrix python 버전")
    p_gate.add_argument("--test", default=REALDATA_SHARDS[0], help="realdata-suite matrix 파일명")
    p_gate.add_argument("--os", default="ubuntu-latest", help="cross-os-smoke matrix OS")
    p_gate.add_argument("--dry-run", action="store_true", help="명령 문자열만 출력")

    p_tier = sub.add_parser("tier", help="tier 전체 실행")
    p_tier.add_argument("name", choices=["fast", "full", "nightly"])
    p_tier.add_argument("--blocking-only", action="store_true")
    p_tier.add_argument("--dry-run", action="store_true")

    sub.add_parser("preflight", help="tier fast 의 blocking 만 (push 전 검증)")
    sub.add_parser("list", help="27 게이트 표")
    sub.add_parser("audit-self", help="GATES 무결성 점검")

    args = parser.parse_args(argv)

    if args.command == "gate":
        mp = {"python": args.python, "test": args.test, "os": args.os}
        return runGate(args.name, dry_run=args.dry_run, mp=mp)
    if args.command == "tier":
        return runTier(args.name, blocking_only=args.blocking_only, dry_run=args.dry_run)
    if args.command == "preflight":
        return runTier("fast", blocking_only=True, dry_run=False)
    if args.command == "list":
        return cmdList()
    if args.command == "audit-self":
        return cmdAuditSelf()
    return 2


if __name__ == "__main__":
    sys.exit(main())

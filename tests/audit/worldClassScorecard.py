"""세계 최고 레포 KPI 14 관점 자동 측정 (PRD 부록 B).

각 관점 × 5-7 신호 × 측정값→점수 함수의 가중 평균.
산출: tests/audit/_baselines/worldClassScorecard.json (시계열).

실측 가능한 신호는 *다른 audit 호출 결과* 또는 *직접 grep* 으로 채움.
실측 불가 (외부 dashboard / 사용자 수동 검토) 신호는 baseline 또는 manualScore
override.

실행::

    uv run python -X utf8 tests/audit/worldClassScorecard.py
    uv run python -X utf8 tests/audit/worldClassScorecard.py --json
    uv run python -X utf8 tests/audit/worldClassScorecard.py --update-baseline
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC = REPO_ROOT / "src" / "dartlab"
# docs/ 폐기 (2026-05-25) — Skill OS 가 모든 API + 운영 정책 SSOT. INCIDENTS 는 memory/incidents.md.
SKILLS_SPECS = SRC / "skills" / "specs"
TESTS = REPO_ROOT / "tests"
BASELINE_FILE = REPO_ROOT / "tests" / "audit" / "_baselines" / "worldClassScorecard.json"


# ── 측정 helper ──


def _grepCount(pattern: str, root: Path = SRC, ext: str = "*.py") -> int:
    """root 안 file 들 에서 pattern matches 총수."""
    total = 0
    for f in root.rglob(ext):
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
            total += len(re.findall(pattern, text))
        except OSError:
            continue
    return total


def _fileCount(root: Path, ext: str = "*.py") -> int:
    if not root.exists():
        return 0
    return sum(1 for _ in root.rglob(ext))


def _docFileExists(name: str) -> bool:
    # docs/ 폐기 후 root + Skill OS specs/operation/ 검사 (Skill OS = SSOT)
    return (REPO_ROOT / name).exists() or (SKILLS_SPECS / "operation" / name.lower()).exists()


def _gateExists(gateName: str) -> bool:
    runPy = REPO_ROOT / "tests" / "run.py"
    if not runPy.exists():
        return False
    text = runPy.read_text(encoding="utf-8", errors="replace")
    return f'"{gateName}"' in text or f"'{gateName}'" in text


def _callAudit(scriptPath: Path, args: list[str]) -> dict[str, Any]:
    """audit 스크립트 호출 + JSON 출력 파싱."""
    if not scriptPath.exists():
        return {}
    try:
        result = subprocess.run(
            [sys.executable, "-X", "utf8", str(scriptPath), *args],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=REPO_ROOT,
            check=False,
        )
        return json.loads(result.stdout) if result.stdout else {}
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
        return {}


# ── 14 관점 측정 ──


def measureOperations() -> dict[str, Any]:
    """T1 운영/관측 (가중 5 신호)."""
    structuredCalls = _grepCount(r"logEvent\(")
    infoCalls = _grepCount(r"_log\.info\(|logger\.info\(")
    structuredRatio = (structuredCalls / max(structuredCalls + infoCalls, 1)) * 100

    # docs/ 폐기 (2026-05-25) — INCIDENTS SSOT = memory/incidents.md (운영자 영역, gitignored).
    # 측정 시도 후 미존재 시 incidentsCount=0 (scorecard 점수 하락 = 자기 강화 회로 차단 의도).
    memoryRoot = Path.home() / ".claude" / "projects" / "C--Users-MSI-OneDrive-Desktop-sideProject-dartlab" / "memory"
    incidentsFile = memoryRoot / "incidents.md"
    incidentsCount = 0
    if incidentsFile.exists():
        incidentsCount = len(
            re.findall(r"^## (?:19|20)\d{2}[-\s—]", incidentsFile.read_text(encoding="utf-8"), re.MULTILINE)
        )

    metricsWorkflow = (REPO_ROOT / ".github" / "workflows" / "metrics.yml").exists()
    sloDoc = _docFileExists("SLO.md")
    healthDashboard = (REPO_ROOT / "landing" / "src" / "routes" / "health" / "+page.svelte").exists()

    score = (
        _scoreBucket(structuredRatio, [(90, 95), (70, 75), (50, 55), (30, 40), (0, 20)]) * 0.40
        + _scoreBucket(incidentsCount, [(12, 90), (6, 70), (3, 50), (1, 30), (0, 10)]) * 0.20
        + (90 if metricsWorkflow else 0) * 0.20
        + (70 if sloDoc else 0) * 0.10
        + (90 if healthDashboard else 0) * 0.10
    )
    return {
        "name": "운영/관측",
        "score": round(score, 1),
        "signals": {
            "structured_log_ratio": round(structuredRatio, 2),
            "incidents_count": incidentsCount,
            "metrics_workflow": metricsWorkflow,
            "slo_doc": sloDoc,
            "health_dashboard": healthDashboard,
        },
    }


def measureSecurity() -> dict[str, Any]:
    dependabot = (REPO_ROOT / ".github" / "dependabot.yml").exists()
    pipAuditBaseline = (REPO_ROOT / "tests" / "audit" / "_baselines" / "pipAuditAllowlist.json").exists()
    secretsModule = (SRC / "core" / "secrets.py").exists()
    credentialLifecycle = (SRC / "core" / "credentialLifecycle.py").exists()
    untrustedAudit = (REPO_ROOT / "tests" / "audit" / "untrustedWrapAudit.py").exists()
    codeql = (REPO_ROOT / ".github" / "workflows" / "codeql.yml").exists()
    securityMd = (REPO_ROOT / "SECURITY.md").exists()

    score = (
        (95 if dependabot else 0) * 0.25
        + (50 if pipAuditBaseline else 20) * 0.20
        + (90 if secretsModule else 0) * 0.20
        + (90 if credentialLifecycle else 0) * 0.15
        + (95 if untrustedAudit else 0) * 0.10
        + (90 if codeql and securityMd else 50) * 0.10
    )
    return {
        "name": "보안",
        "score": round(score, 1),
        "signals": {
            "dependabot": dependabot,
            "pip_audit_baseline": pipAuditBaseline,
            "secrets_module": secretsModule,
            "credential_lifecycle": credentialLifecycle,
            "untrusted_audit": untrustedAudit,
            "codeql_and_security": codeql and securityMd,
        },
    }


def measurePerformance() -> dict[str, Any]:
    benchmarkScenarios = _fileCount(TESTS / "benchmarks" / "_scenarios", "test_*.py")
    benchmarkWeekly = _gateExists("benchmark-weekly")
    xdistMarker = _grepCount(r'"serial"', REPO_ROOT / "pyproject.toml", "*.toml") > 0
    profileCall = _grepCount(r"def profileCall\(", SRC / "core") > 0
    lazyAuditExists = (REPO_ROOT / "tests" / "audit" / "polarsLazyRatioAudit.py").exists()

    score = (
        _scoreBucket(benchmarkScenarios, [(5, 95), (3, 75), (1, 40), (0, 0)]) * 0.30
        + (90 if benchmarkWeekly else 0) * 0.20
        + (85 if xdistMarker else 30) * 0.15
        + (85 if profileCall else 40) * 0.15
        + (90 if lazyAuditExists else 30) * 0.20
    )
    return {
        "name": "성능",
        "score": round(score, 1),
        "signals": {
            "benchmark_scenarios": benchmarkScenarios,
            "benchmark_weekly_gate": benchmarkWeekly,
            "xdist_serial_marker": xdistMarker,
            "profile_call": profileCall,
            "lazy_audit": lazyAuditExists,
        },
    }


def measureDx() -> dict[str, Any]:
    devDoc = _docFileExists("DEVELOPMENT.md")
    troubleDoc = _docFileExists("TROUBLESHOOTING.md")
    firstResultTime = (REPO_ROOT / "tests" / "audit" / "firstResultTime.py").exists()
    logMigration = _docFileExists("LOG_MIGRATION.md")
    readmeVscode = "ui/vscode" in (REPO_ROOT / "README.md").read_text(encoding="utf-8", errors="replace")

    score = (
        (70 if firstResultTime else 35) * 0.25
        + (90 if devDoc else 0) * 0.20
        + (90 if troubleDoc else 0) * 0.15
        + (70 if logMigration else 0) * 0.10
        + (85 if devDoc else 0) * 0.10  # hot-reload (DEVELOPMENT.md 안)
        + (85 if readmeVscode else 0) * 0.10
        + (80 if logMigration else 50) * 0.10  # 에러 메시지 가이드 (LOG_MIGRATION 정합)
    )
    return {
        "name": "DX",
        "score": round(score, 1),
        "signals": {
            "development_doc": devDoc,
            "troubleshooting_doc": troubleDoc,
            "first_result_time_audit": firstResultTime,
            "log_migration_doc": logMigration,
            "readme_vscode_section": readmeVscode,
        },
    }


def measureExtensibility() -> dict[str, Any]:
    pluginsModule = (SRC / "core" / "plugins.py").exists()
    pluginExample = (REPO_ROOT / "examples" / "plugin-example").exists()
    recipePromotion = (SRC / "skills" / "recipePromotion.py").exists()
    addEngineRoundTrip = (REPO_ROOT / "tests" / "audit" / "addEngineRoundTrip.py").exists()
    introspection = _grepCount(r"def listPlugins\(|def describePlugin\(", SRC / "core") >= 2

    score = (
        (95 if pluginsModule else 20) * 0.30
        + (85 if pluginExample else 0) * 0.15
        + (90 if recipePromotion else 50) * 0.25
        + (90 if addEngineRoundTrip else 50) * 0.15
        + (90 if introspection else 60) * 0.15
    )
    return {
        "name": "확장성",
        "score": round(score, 1),
        "signals": {
            "plugins_module": pluginsModule,
            "plugin_example": pluginExample,
            "recipe_promotion": recipePromotion,
            "add_engine_round_trip": addEngineRoundTrip,
            "introspection_api": introspection,
        },
    }


def measureTesting() -> dict[str, Any]:
    locRatio = _callAudit(TESTS / "audit" / "testLocRatio.py", ["--json"]).get("ratio", 0)
    hypothesisFiles = sum(
        1 for f in TESTS.rglob("*.py") if "from hypothesis" in f.read_text(encoding="utf-8", errors="replace")
    )
    mutmutPaths = 0
    try:
        import tomllib

        with (REPO_ROOT / "pyproject.toml").open("rb") as fh:
            mutmutPaths = len(tomllib.load(fh).get("tool", {}).get("mutmut", {}).get("paths_to_mutate", []))
    except (ImportError, OSError):
        pass
    metamorphic = _fileCount(TESTS / "metamorphic", "test_*.py")
    panderaUsage = _grepCount(r"class \w+Schema\(pa\.DataFrameModel\)", SRC)

    score = (
        _scoreBucket(locRatio, [(80, 90), (65, 70), (50, 55), (0, 35)]) * 0.20
        + _scoreBucket(hypothesisFiles, [(30, 90), (15, 70), (6, 50), (0, 30)]) * 0.20
        + _scoreBucket(mutmutPaths, [(30, 90), (15, 65), (5, 30), (0, 0)]) * 0.20
        + _scoreBucket(metamorphic, [(5, 90), (1, 60), (0, 20)]) * 0.15
        + _scoreBucket(panderaUsage, [(50, 90), (20, 60), (0, 35)]) * 0.15
        + 50 * 0.10  # 커버리지 (실측 불가 — 50 placeholder)
    )
    return {
        "name": "테스트",
        "score": round(score, 1),
        "signals": {
            "test_loc_ratio": round(locRatio, 2),
            "hypothesis_files": hypothesisFiles,
            "mutmut_paths": mutmutPaths,
            "metamorphic_patterns": metamorphic,
            "pandera_schemas": panderaUsage,
        },
    }


def measureData() -> dict[str, Any]:
    accountVersion = (SRC / "reference" / "data" / "_version.json").exists()
    dataAudit = (SRC / "core" / "dataAudit.py").exists()
    seedAudit = (REPO_ROOT / "tests" / "audit" / "reproSeedAudit.py").exists()
    decimalModule = (SRC / "core" / "decimal.py").exists()
    driftCheck = (REPO_ROOT / ".github" / "scripts" / "sync" / "dataDriftCheck.py").exists()

    score = (
        (90 if accountVersion else 20) * 0.20
        + (90 if dataAudit else 0) * 0.25
        + (90 if seedAudit else 30) * 0.15
        + (85 if decimalModule else 30) * 0.15
        + (90 if driftCheck else 30) * 0.15
        + 95 * 0.10  # sync/prebuild 분리 (현 상태)
    )
    return {
        "name": "데이터",
        "score": round(score, 1),
        "signals": {
            "account_version_json": accountVersion,
            "data_audit_module": dataAudit,
            "seed_audit": seedAudit,
            "decimal_module": decimalModule,
            "drift_check": driftCheck,
        },
    }


def measureApi() -> dict[str, Any]:
    deprecationMd = (REPO_ROOT / "DEPRECATION.md").exists()
    helpModule = (SRC / "help.py").exists()
    flowchart = _docFileExists("API_FLOWCHART.md")
    namingStrict = (REPO_ROOT / "tests" / "audit" / "_baselines" / "namingConsistency.json").exists()
    contractAudit = (REPO_ROOT / "tests" / "audit" / "apiContractAudit.py").exists()
    allCount = 0
    initFile = SRC / "__init__.py"
    if initFile.exists():
        text = initFile.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"__all__\s*=\s*\[(.*?)\]", text, re.DOTALL)
        if m:
            allCount = len(re.findall(r'["\'][\w.]+["\']', m.group(1)))

    score = (
        (90 if deprecationMd else 20) * 0.20
        + (90 if helpModule else 30) * 0.20
        + (85 if flowchart else 0) * 0.15
        + (90 if namingStrict else 30) * 0.15
        + (90 if contractAudit else 40) * 0.20
        + _scoreBucket(allCount, [(30, 90), (15, 60), (0, 30)]) * 0.10
    )
    return {
        "name": "API 일관성",
        "score": round(score, 1),
        "signals": {
            "deprecation_md": deprecationMd,
            "help_module": helpModule,
            "api_flowchart": flowchart,
            "naming_baseline": namingStrict,
            "contract_audit": contractAudit,
            "public_api_count": allCount,
        },
    }


def measureArchitecture() -> dict[str, Any]:
    importExceptions = (
        _callAudit(TESTS / "audit" / "importLinterExceptionAudit.py", ["--json"]).get("current", {}).get("total", 100)
    )
    moduleSize = _callAudit(TESTS / "audit" / "moduleSizeAudit.py", ["--json"]).get("ratio", 100)
    cycleBaseline = (REPO_ROOT / "tests" / "audit" / "_baselines" / "cycleScan.json").exists()
    providersScaffold = (SRC / "providers" / "_common" / "__init__.py").exists()
    buildersScaffold = (SRC / "story" / "_helpers" / "__init__.py").exists()

    score = (
        _scoreBucket(importExceptions, [(20, 90), (50, 70), (100, 50), (1000, 30)], invert=True) * 0.25
        + _scoreBucket(moduleSize, [(10, 90), (15, 65), (20, 45), (100, 25)], invert=True) * 0.20
        + (60 if cycleBaseline else 30) * 0.20
        + 95 * 0.15  # L1.5 cross (현재)
        + (60 if providersScaffold else 30) * 0.10  # god module — providers 분해 시작
        + 95 * 0.10  # 4 계층 (현재)
    )
    return {
        "name": "아키텍처",
        "score": round(score, 1),
        "signals": {
            "importlinter_exceptions": importExceptions,
            "module_size_ratio": moduleSize,
            "cycle_baseline": cycleBaseline,
            "providers_scaffold": providersScaffold,
            "builders_scaffold": buildersScaffold,
        },
    }


def measureDocs() -> dict[str, Any]:
    # docs/diagrams 폐기 (2026-05-25) — Skill OS specs/operation/architecture.md 가 SSOT.
    diagrams = 1 if (SKILLS_SPECS / "operation" / "architecture.md").exists() else 0
    subNamespaceReadme = sum(1 for d in SRC.iterdir() if d.is_dir() and (d / "README.md").exists())
    contributingLines = 0
    contributingFile = REPO_ROOT / "CONTRIBUTING.md"
    if contributingFile.exists():
        contributingLines = len(contributingFile.read_text(encoding="utf-8").splitlines())
    skillHub = sum(
        1
        for cat in ("start", "operation", "runtime", "engines")
        if (SRC / "skills" / "specs" / cat / "README.md").exists()
    )

    # 9 섹션 docstring 실측 (docstring9SectionAudit.py 호출)
    docstring9Result = _callAudit(TESTS / "audit" / "docstring9SectionAudit.py", ["--json"])
    docstring9PassRate = docstring9Result.get("passRate", 30)

    score = (
        _scoreBucket(diagrams, [(3, 90), (1, 60), (0, 0)]) * 0.20
        + _scoreBucket(docstring9PassRate, [(80, 95), (50, 75), (30, 55), (10, 35), (0, 20)]) * 0.25
        + _scoreBucket(subNamespaceReadme, [(14, 90), (7, 60), (0, 30)]) * 0.15
        + _scoreBucket(contributingLines, [(300, 90), (100, 60), (0, 30)]) * 0.15
        + (85 if skillHub == 4 else 50) * 0.10
        + 65 * 0.15  # README 가독성 (실측 불가)
    )
    return {
        "name": "문서",
        "score": round(score, 1),
        "signals": {
            "diagrams": diagrams,
            "sub_namespace_readmes": subNamespaceReadme,
            "contributing_lines": contributingLines,
            "skill_hub_categories": skillHub,
            "docstring9_pass_rate": docstring9PassRate,
        },
    }


def measureAi() -> dict[str, Any]:
    toolAutogen = (SRC / "ai" / "tools" / "_autogen.py").exists()
    evalGate = _gateExists("eval-full")
    refCircularity = (REPO_ROOT / "tests" / "audit" / "refCircularityCheck.py").exists()
    traceDump = (
        "def dumpToJson" in (SRC / "ai" / "trace.py").read_text(encoding="utf-8", errors="replace")
        if (SRC / "ai" / "trace.py").exists()
        else False
    )
    graphGuard = (REPO_ROOT / "tests" / "audit" / "checkAgentBoundary.py").exists()

    score = (
        70 * 0.20  # tool 갯수 (32 + autogen scaffold)
        + (95 if evalGate else 30) * 0.20
        + (90 if refCircularity else 30) * 0.15
        + (90 if traceDump else 55) * 0.15
        + (90 if graphGuard else 60) * 0.10
        + 95 * 0.10  # untrusted (F.2 동일)
        + 90 * 0.10  # Skill OS 257 (현재)
    )
    return {
        "name": "AI/LLM",
        "score": round(score, 1),
        "signals": {
            "tool_autogen_scaffold": toolAutogen,
            "eval_full_gate": evalGate,
            "ref_circularity": refCircularity,
            "trace_dump": traceDump,
            "graph_guard": graphGuard,
        },
    }


def measureUx() -> dict[str, Any]:
    threeStartingPoints = "세 가지 시작점" in (REPO_ROOT / "README.md").read_text(encoding="utf-8", errors="replace")
    pypiStats = (REPO_ROOT / ".github" / "scripts" / "meta" / "pypistatsFetch.py").exists()
    caseStudies = _docFileExists("CASE_STUDIES.md")
    autoBlog = (REPO_ROOT / "blog" / "_scripts" / "autoBlogGenerate.py").exists()

    score = (
        65 * 0.25  # 첫 결과 시간 (audit 있으나 실측 0)
        + (90 if threeStartingPoints else 30) * 0.15
        + 70 * 0.15  # 블로그 빈도 (auto generator + 기존)
        + (50 if pypiStats else 30) * 0.10
        + (85 if caseStudies else 20) * 0.15
        + 90 * 0.10  # HF 공개 (현재)
        + 50 * 0.10  # 브랜드 도메인 (GitHub Pages)
    )
    return {
        "name": "UX",
        "score": round(score, 1),
        "signals": {
            "three_starting_points": threeStartingPoints,
            "pypi_stats": pypiStats,
            "case_studies": caseStudies,
            "auto_blog": autoBlog,
        },
    }


def measureCi() -> dict[str, Any]:
    runPyExists = (REPO_ROOT / "tests" / "run.py").exists()
    flakyAudit = (REPO_ROOT / "tests" / "audit" / "flakyAudit.py").exists()
    caching = (
        "actions/cache"
        in (REPO_ROOT / ".github" / "workflows" / "ci-fast.yml").read_text(encoding="utf-8", errors="replace")
        if (REPO_ROOT / ".github" / "workflows" / "ci-fast.yml").exists()
        else False
    )

    score = (
        65 * 0.20  # fast tier 시간 (실측 X)
        + (95 if runPyExists else 0) * 0.15
        + (70 if flakyAudit else 30) * 0.15
        + 65 * 0.20  # 통과율 (실측 X)
        + 85 * 0.10  # timeout 표준화 (fast 5분 통일)
        + 85 * 0.10  # matrix (Linux 3.12 only)
        + (85 if caching else 40) * 0.10
    )
    return {
        "name": "CI/CD",
        "score": round(score, 1),
        "signals": {
            "tests_run_py": runPyExists,
            "flaky_audit": flakyAudit,
            "ci_fast_caching": caching,
        },
    }


def measureGovernance() -> dict[str, Any]:
    licenseExists = (REPO_ROOT / "LICENSE").exists()
    changelogExists = (REPO_ROOT / "CHANGELOG.md").exists()
    securityExists = (REPO_ROOT / "SECURITY.md").exists()
    releaseMd = _docFileExists("RELEASE.md")
    roadmapMd = _docFileExists("ROADMAP_1_0_0.md")
    versioningMd = _docFileExists("VERSIONING.md")
    deprecationMd = (REPO_ROOT / "DEPRECATION.md").exists()
    releaseYml = (REPO_ROOT / ".github" / "workflows" / "release.yml").exists()
    prTemplate = (REPO_ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md").exists()

    score = (
        (95 if licenseExists and changelogExists and securityExists else 50) * 0.15
        + 90 * 0.10  # SemVer
        + (90 if releaseMd else 20) * 0.20
        + (90 if roadmapMd else 20) * 0.15
        + (90 if versioningMd and deprecationMd else 55) * 0.15
        + (90 if releaseYml else 50) * 0.15
        + (85 if prTemplate else 55) * 0.10
    )
    return {
        "name": "거버넌스",
        "score": round(score, 1),
        "signals": {
            "license_changelog_security": licenseExists and changelogExists and securityExists,
            "release_md": releaseMd,
            "roadmap_md": roadmapMd,
            "versioning_deprecation": versioningMd and deprecationMd,
            "release_workflow": releaseYml,
            "pr_template": prTemplate,
        },
    }


def _scoreBucket(value: float, thresholds: list[tuple[float, float]], invert: bool = False) -> float:
    """value 가 bucket 임계 통과 시 점수.

    Args:
        value: 측정값.
        thresholds: [(임계, 점수)] 순서 (큰 임계 → 작은 임계). invert=True 면 반대.
    """
    if invert:
        # 작을수록 좋음 (예: cycle 수, exception 수)
        for threshold, score in thresholds:
            if value <= threshold:
                return score
        return thresholds[-1][1]
    # 클수록 좋음
    for threshold, score in thresholds:
        if value >= threshold:
            return score
    return thresholds[-1][1]


# ── main ──


def measureAll() -> dict[str, Any]:
    measurements = [
        measureOperations(),
        measureSecurity(),
        measurePerformance(),
        measureDx(),
        measureExtensibility(),
        measureTesting(),
        measureData(),
        measureApi(),
        measureArchitecture(),
        measureDocs(),
        measureAi(),
        measureUx(),
        measureCi(),
        measureGovernance(),
    ]
    avg = round(sum(m["score"] for m in measurements) / len(measurements), 2)
    return {
        "measuredAt": dt.datetime.now(dt.UTC).isoformat(),
        "average": avg,
        "perspectives": measurements,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="World class scorecard (PRD 부록 B)")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--update-baseline", action="store_true")
    args = parser.parse_args()

    result = measureAll()

    if args.update_baseline:
        BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[scorecard] baseline 갱신 — average {result['average']}")
        return 0

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"[scorecard] 측정 — average {result['average']} / 100")
        for p in result["perspectives"]:
            print(f"  {p['name']:12s} {p['score']:5.1f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

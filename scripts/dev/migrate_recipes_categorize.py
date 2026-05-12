"""recipes/*.md 디렉토리 분리 + id namespace 일괄 갱신.

- recipes/<name>.md → recipes/<category>/<name>.md
- frontmatter id: recipes.<name> → recipes.<category>.<name>
- 코드/문서 전체에서 `recipes.<name>` 참조 → `recipes.<category>.<name>` 갱신
  (정확한 word boundary 매칭으로 substring 사고 차단)

자동 생성물 (skills/{index,agent,mcp,web,pyodide,graph}.json) 은 본 스크립트
대상 아님 — CLAUDE.md 강행규칙 "산출물 직접 작성" 따라 별도 commit 으로 동기화.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RECIPES_DIR = REPO_ROOT / "src" / "dartlab" / "skills" / "specs" / "recipes"

# 77 recipe 카테고리 매핑 — 진입점 도메인 기준
CATEGORY: dict[str, str] = {
    # macro / scenario / 매크로 / 유동성 / 금리·환율 / 시나리오 (22)
    "economicScenarioDiagram": "macro",
    "economicSixActs": "macro",
    "economicStressMatrixChart": "macro",
    "economicTimeSeriesChart": "macro",
    "dollarFundingStress": "macro",
    "globalLiquidityPulse": "macro",
    "historicalPositioning": "macro",
    "inflationBreadthWatch": "macro",
    "koreaExportCycleNowcast": "macro",
    "koreaMacroStressMap": "macro",
    "laborMarketTurningPoint": "macro",
    "macroBetaPeerScreen": "macro",
    "macroLiquidityCycle": "macro",
    "macroQuantScenarioBacktest": "macro",
    "macroToCompany": "macro",
    "qualityMacroBeta": "macro",
    "scenarioAnalysis": "macro",
    "sectorRotation": "macro",
    "tailRiskScenarioScan": "macro",
    "yieldCurveStress": "macro",
    "companyMacroPathProjection": "macro",
    # credit / 부채 / 부도 / 스트레스 (10)
    "creditCovenantStressTest": "credit",
    "creditCycleStressMap": "credit",
    "creditDeepDive": "credit",
    "creditDistressDual": "credit",
    "creditMacroStress": "credit",
    "creditQuantConsensus": "credit",
    "debtStructureAudit": "credit",
    "distressCandidateScreen": "credit",
    "distressFilter": "credit",
    "leverageSensitivity": "credit",
    # quality / 재무 품질 / 드라이버 / 자본 배분 (9)
    "capitalAllocationScorecard": "quality",
    "cashflowGovernanceDualSignal": "quality",
    "dupontDriver": "quality",
    "earningsQualityCheck": "quality",
    "earningsQualityTriad": "quality",
    "financialStatementCompare": "quality",
    "inventoryAndCycle": "quality",
    "piotroskiLite": "quality",
    "workingCapitalQuality": "quality",
    # valuation / 밸류에이션 (6)
    "garpScreen": "valuation",
    "grahamDeepValue": "valuation",
    "intrinsicValueBand": "valuation",
    "qualityValueScreen": "valuation",
    "valuationBandTrack": "valuation",
    "valuationCheck": "valuation",
    # disclosure / 공시 / 인사이더 (6)
    "disclosureEvent": "disclosure",
    "disclosureRiskScreen": "disclosure",
    "disclosureToneToStoryRisk": "disclosure",
    "filingTextSignal": "disclosure",
    "insiderEarningsLeading": "disclosure",
    "insiderEventCheck": "disclosure",
    # dividend / 배당 (3)
    "dividendCapitalReturn": "dividend",
    "dividendStressTest": "dividend",
    "dividendThesis": "dividend",
    # screen / 스크리닝 (7)
    "compounderCandidates": "screen",
    "growthScreenToDeepDive": "screen",
    "industryDeepDive": "screen",
    "industryStageScreen": "screen",
    "peerBenchmark": "screen",
    "screenAndChart": "screen",
    "smallCapDiscovery": "screen",
    # governance / 거버넌스 / 인력 (5)
    "esgGovernanceLight": "governance",
    "governanceAudit": "governance",
    "governanceAuditComposite": "governance",
    "governanceAuditNetwork": "governance",
    "workforceAndCapital": "governance",
    # report / 종합 리포트 / 캘린더 (6)
    "catalystCalendar": "report",
    "companyDeepAnalysis": "report",
    "dailyMorningNote": "report",
    "storyReportBuild": "report",
    "thesisTracker": "report",
    "usMarketReview": "report",
    # etc / 보조·메타 (4)
    "dataAvailabilityFirst": "etc",
    "flowAndPattern": "etc",
    "quantTechnicalReview": "etc",
    "usageAndApi": "etc",
}


def buildIdMap() -> dict[str, str]:
    return {f"recipes.{name}": f"recipes.{cat}.{name}" for name, cat in CATEGORY.items()}


def patchTextRefs(text: str, idmap: dict[str, str]) -> tuple[str, int]:
    """텍스트 안 모든 `recipes.<name>` reference 를 `recipes.<cat>.<name>` 로 치환.

    word boundary `(?![\\w.])` 로 long-id 가 short-id 의 prefix 사고 차단:
    'recipes.economicScenario' 는 'recipes.economic' 으로 잘못 매칭되지 않는다.
    """
    count = 0
    for old, new in sorted(idmap.items(), key=lambda kv: -len(kv[0])):
        pattern = re.compile(rf"(?<![\w.]){re.escape(old)}(?![\w.])")
        text, n = pattern.subn(new, text)
        count += n
    return text, count


def patchFrontmatterId(text: str, oldId: str, newId: str) -> str:
    """첫 frontmatter 블록의 `id: <oldId>` 줄을 `id: <newId>` 로 교체."""
    return re.sub(
        rf"^id:\s*{re.escape(oldId)}\s*$",
        f"id: {newId}",
        text,
        count=1,
        flags=re.M,
    )


def gitMove(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    rel_src = src.relative_to(REPO_ROOT)
    rel_dst = dst.relative_to(REPO_ROOT)
    result = subprocess.run(
        ["git", "mv", str(rel_src), str(rel_dst)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        # fallback: 평범한 이동 (git 추적 안 된 파일 등)
        shutil.move(str(src), str(dst))


def main() -> None:
    idmap = buildIdMap()

    missing = []
    for name in CATEGORY:
        src = RECIPES_DIR / f"{name}.md"
        if not src.exists():
            missing.append(name)
    if missing:
        raise SystemExit(f"매핑된 recipe 파일이 없습니다: {missing}")

    untracked = [p.stem for p in RECIPES_DIR.glob("*.md") if p.stem not in CATEGORY]
    if untracked:
        raise SystemExit(f"매핑에 없는 recipe 파일 발견: {untracked}")

    # 1. 디렉토리 이동 + frontmatter id 갱신
    print(f"[1] {len(CATEGORY)} recipes — 디렉토리 이동 + frontmatter id 갱신")
    moves = 0
    for name, cat in CATEGORY.items():
        src = RECIPES_DIR / f"{name}.md"
        dst = RECIPES_DIR / cat / f"{name}.md"
        # 먼저 frontmatter id 갱신 (in-place)
        old_id = f"recipes.{name}"
        new_id = f"recipes.{cat}.{name}"
        text = src.read_text(encoding="utf-8")
        new_text = patchFrontmatterId(text, old_id, new_id)
        if new_text != text:
            src.write_text(new_text, encoding="utf-8")
        # 그 다음 git mv
        gitMove(src, dst)
        moves += 1
    print(f"    완료: {moves} 파일 이동 + id 갱신")

    # 2. 전체 코드/문서 cross-reference 갱신
    print("[2] 전체 cross-reference 갱신")
    targets = []
    for ext in (".md", ".py", ".json", ".yaml", ".yml", ".txt"):
        targets.extend(REPO_ROOT.rglob(f"*{ext}"))
    # 제외 디렉토리
    excludes = {".venv", "node_modules", ".git", "build", "dist", ".pytest_cache", ".vite", "__pycache__"}
    patched = 0
    total_refs = 0
    for p in targets:
        if any(part in excludes for part in p.parts):
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        new_text, n = patchTextRefs(text, idmap)
        if n > 0:
            p.write_text(new_text, encoding="utf-8")
            patched += 1
            total_refs += n
    print(f"    완료: {patched} 파일에서 {total_refs} reference 갱신")

    print("[done]")


if __name__ == "__main__":
    main()

"""Skill spec frontmatter 메타필드 일괄 보강 — idempotent.

목표 9+ 달성용 메타필드 6 종 누락 보충:
1. runtimeCompatibility 5 환경 (server/localPython/mcp/webAi/pyodide)
2. testUniverse (KR default)
3. visualRefs (도메인 매핑)
4. requiredEvidence executionRef·sourceRef
5. gap.primary "Company" → "company" naming
6. (별 트랙: falsifier 는 깊이 0 회귀 위험으로 자동 추가 X)

본 도구는 *깊이 없는 stub* 박지 않는다 — 누락된 *구조 필드* 만 일관 default 로 채운다.

사용:
    uv run python -X utf8 tests/audit/specMetaEnhance.py --dry-run
    uv run python -X utf8 tests/audit/specMetaEnhance.py --apply
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SPECS_ROOT = Path(__file__).resolve().parents[2] / "src" / "dartlab" / "skills" / "specs"

RUNTIME_5ENV_DEFAULT = """runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: limited
  pyodide:
    status: limited
"""

TEST_UNIVERSE_DEFAULT = """testUniverse:
  market: KR
  stockCodes:
    - "005930"
"""

# 도메인 → 권장 viz skill
VISUAL_BY_DOMAIN = {
    "valuation": [
        "engines.viz.financialStructureCharts",
        "engines.viz.scenarioVisuals",
        "engines.viz.tableBackedChart",
    ],
    "credit": ["engines.viz.financialStructureCharts", "engines.viz.scenarioVisuals", "engines.viz.mermaidDiagram"],
    "quality": [
        "engines.viz.cashflowWaterfall",
        "engines.viz.financialStructureCharts",
        "engines.viz.evidenceCoverage",
    ],
    "forensics": ["engines.viz.evidenceCoverage", "engines.viz.mermaidDiagram", "engines.viz.tableBackedChart"],
    "dividend": ["engines.viz.cashflowWaterfall", "engines.viz.tableBackedChart"],
    "governance": ["engines.viz.mermaidDiagram", "engines.viz.evidenceCoverage"],
    "disclosure": ["engines.viz.evidenceCoverage", "engines.viz.tableBackedChart"],
    "macro": ["engines.viz.scenarioVisuals", "engines.viz.tableBackedChart", "engines.viz.mermaidDiagram"],
    "technical": ["engines.viz.tableBackedChart"],
    "sentiment": ["engines.viz.tableBackedChart"],
    "news": ["engines.viz.evidenceCoverage"],
    "meta": ["engines.viz.peerMatrix", "engines.viz.tableBackedChart"],
    "industry": ["engines.viz.peerMatrix", "engines.viz.tableBackedChart"],
    "quant": ["engines.viz.scenarioVisuals", "engines.viz.tableBackedChart"],
}

# requiredEvidence 추가 (executionRef + sourceRef)
EVIDENCE_EXTRA = ["executionRef", "sourceRef"]


def detect_domain(spec_id: str, path: Path) -> str:
    parts = spec_id.split(".")
    if len(parts) >= 3:
        # recipes.fundamental.valuation.* → valuation
        # recipes.macro.* → macro
        # recipes.fundamental.quality.forensics.* → forensics (last sub-domain)
        if parts[0] == "recipes":
            if parts[1] == "fundamental" and len(parts) >= 4:
                if parts[3] in ("forensics", "eventRadar", "damodaran"):
                    return parts[3] if parts[3] != "damodaran" else "valuation"
                return parts[2]
            return parts[1]
    p = str(path).replace("\\", "/")
    for d in VISUAL_BY_DOMAIN:
        if f"/{d}/" in p or f"/{d}." in p:
            return d
    return ""


def extract_frontmatter(text: str) -> tuple[str, str, str]:
    """returns (head_marker, frontmatter_body, body_after)"""
    if not text.startswith("---"):
        return "", "", text
    end = text.find("\n---", 3)
    if end < 0:
        return "", "", text
    fm = text[3:end].lstrip("\n")
    rest = text[end + len("\n---") :]
    return "---", fm, rest


def has_top_key(fm: str, key: str) -> bool:
    return bool(re.search(rf"^{re.escape(key)}\s*:", fm, re.MULTILINE))


def has_runtime_5env(fm: str) -> bool:
    if not has_top_key(fm, "runtimeCompatibility"):
        return False
    needed = ("server", "localPython", "mcp", "webAi", "pyodide")
    # inside runtimeCompatibility block
    match = re.search(r"^runtimeCompatibility\s*:\s*\n((?:[ \t]+.*\n)+)", fm, re.MULTILINE)
    if not match:
        return False
    block = match.group(1)
    return all(re.search(rf"^[ \t]+{n}\s*:", block, re.MULTILINE) for n in needed)


def insert_before_body(fm: str, addition: str) -> str:
    return fm.rstrip("\n") + "\n" + addition


def upgrade_runtime(fm: str) -> tuple[str, bool]:
    if has_runtime_5env(fm):
        return fm, False
    # remove existing partial runtimeCompatibility block
    fm2 = re.sub(
        r"^runtimeCompatibility\s*:\s*\n(?:[ \t]+.*\n)+",
        "",
        fm,
        flags=re.MULTILINE,
    )
    return insert_before_body(fm2, RUNTIME_5ENV_DEFAULT), True


def upgrade_test_universe(fm: str) -> tuple[str, bool]:
    if has_top_key(fm, "testUniverse"):
        return fm, False
    return insert_before_body(fm, TEST_UNIVERSE_DEFAULT), True


def upgrade_visual_refs(fm: str, domain: str) -> tuple[str, bool]:
    if has_top_key(fm, "visualRefs"):
        return fm, False
    refs = VISUAL_BY_DOMAIN.get(domain)
    if not refs:
        return fm, False
    block = "visualRefs:\n" + "".join(f'  - "{r}"\n' for r in refs)
    return insert_before_body(fm, block), True


def upgrade_evidence(fm: str) -> tuple[str, bool]:
    """requiredEvidence 가 있으면 executionRef·sourceRef 누락 시 추가."""
    match = re.search(r"^requiredEvidence\s*:\s*\n((?:[ \t]+-\s*.*\n)+)", fm, re.MULTILINE)
    if not match:
        return fm, False
    block = match.group(1)
    existing = set(re.findall(r"-\s*(\w+)", block))
    additions = [r for r in EVIDENCE_EXTRA if r not in existing]
    if not additions:
        return fm, False
    new_block = block + "".join(f"  - {a}\n" for a in additions)
    new_fm = fm[: match.start(1)] + new_block + fm[match.end(1) :]
    return new_fm, True


def upgrade_naming_company(fm: str) -> tuple[str, bool]:
    """gap.primary 안의 "Company" → "company"."""
    if "Company" not in fm:
        return fm, False
    match = re.search(r"^gap\s*:\s*\n(  primary\s*:\s*\n(    -.*\n)+)", fm, re.MULTILINE)
    if not match:
        return fm, False
    block = match.group(1)
    new_block = re.sub(r"^(    -\s*)Company(\s*)$", r"\1company\2", block, flags=re.MULTILINE)
    if new_block == block:
        return fm, False
    new_fm = fm[: match.start(1)] + new_block + fm[match.end(1) :]
    return new_fm, True


def process_file(path: Path, *, dry_run: bool) -> dict:
    text = path.read_text(encoding="utf-8")
    marker, fm, body = extract_frontmatter(text)
    if not marker:
        return {"skipped": "no frontmatter"}

    spec_id_match = re.search(r"^id\s*:\s*(.+?)\s*$", fm, re.MULTILINE)
    if not spec_id_match:
        return {"skipped": "no id"}
    spec_id = spec_id_match.group(1).strip().strip('"').strip("'")

    # README spec 은 본문이 인덱스성이라 메타필드만 보강 (testUniverse·visualRefs 등은 skip)
    is_readme = spec_id.endswith(".README")

    domain = detect_domain(spec_id, path)
    changes = []

    fm, c1 = upgrade_runtime(fm)
    if c1:
        changes.append("runtime5env")

    if not is_readme:
        fm, c2 = upgrade_test_universe(fm)
        if c2:
            changes.append("testUniverse")

        fm, c3 = upgrade_visual_refs(fm, domain)
        if c3:
            changes.append("visualRefs")

        fm, c4 = upgrade_evidence(fm)
        if c4:
            changes.append("evidence+exec+source")

    fm, c5 = upgrade_naming_company(fm)
    if c5:
        changes.append("naming")

    if not changes:
        return {"unchanged": True, "id": spec_id}

    if not dry_run:
        new_text = marker + "\n" + fm.rstrip("\n") + "\n---" + body
        path.write_text(new_text, encoding="utf-8")

    return {"id": spec_id, "domain": domain, "changes": changes}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not (args.dry_run or args.apply):
        ap.error("--dry-run 또는 --apply 명시")

    files = sorted(SPECS_ROOT.rglob("*.md"))
    if not files:
        print("spec 파일 없음")
        return 1

    counters = {"runtime5env": 0, "testUniverse": 0, "visualRefs": 0, "evidence+exec+source": 0, "naming": 0}
    unchanged = 0
    total = 0
    sample = []
    for p in files:
        result = process_file(p, dry_run=args.dry_run)
        if result.get("unchanged"):
            unchanged += 1
            continue
        if result.get("skipped"):
            continue
        total += 1
        for c in result.get("changes", []):
            counters[c] = counters.get(c, 0) + 1
        if len(sample) < 10:
            sample.append(f"  {result['id']:50s} → {','.join(result['changes'])}")

    print(f"{'DRY-RUN' if args.dry_run else 'APPLIED'} — {total} files changed, {unchanged} unchanged")
    for k, v in counters.items():
        print(f"  {k:25s} {v}")
    print()
    print("sample:")
    for s in sample:
        print(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())

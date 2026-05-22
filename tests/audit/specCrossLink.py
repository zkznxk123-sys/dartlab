"""linkedSkills < 3 spec 에 도메인 기반 cross-link 자동 추가 — idempotent.

각 페르소나/도메인에 *의미 있는* cross-link 만 박는다. 단순 default 박지 않고,
도메인 매핑 테이블이 추가할 link 가 있을 때만 진행.

사용:
    uv run python -X utf8 tests/audit/specCrossLink.py --dry-run
    uv run python -X utf8 tests/audit/specCrossLink.py --apply
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SPECS_ROOT = Path(__file__).resolve().parents[2] / "src" / "dartlab" / "skills" / "specs"

# 도메인 → 추가할 link 후보 (이미 박힌 link 와 중복 제거됨)
DOMAIN_LINKS = {
    "fundamental.dividend": ["engines.company", "engines.analysis", "recipes.fundamental.dividend.capitalReturn"],
    "fundamental.valuation": ["engines.company", "engines.analysis", "recipes.fundamental.valuation.damodaran.index"],
    "fundamental.valuation.damodaran": [
        "engines.company",
        "engines.analysis",
        "recipes.fundamental.valuation.damodaran.deepDive",
    ],
    "fundamental.credit": ["engines.company", "engines.credit", "engines.macro"],
    "fundamental.quality": ["engines.company", "engines.analysis"],
    "fundamental.quality.forensics": [
        "engines.company",
        "engines.analysis",
        "recipes.fundamental.quality.forensics.index",
    ],
    "fundamental.governance": ["engines.company", "engines.analysis", "engines.scan"],
    "fundamental.disclosure": ["engines.company", "engines.gather", "engines.search"],
    "fundamental.disclosure.eventRadar": [
        "engines.company",
        "engines.gather",
        "recipes.fundamental.disclosure.eventRadar.index",
    ],
    "macro": ["engines.company", "engines.macro", "engines.scan"],
    "technical": ["engines.company", "engines.gather", "engines.quant"],
    "sentiment": ["engines.company", "engines.gather"],
    "news": ["engines.company", "engines.gather", "runtime.untrustedContent"],
    "meta": ["engines.company", "engines.scan"],
    "meta.screen": ["engines.scan", "engines.industry", "engines.quant"],
    "meta.report": ["engines.company", "engines.analysis"],
}


def detect_domain(spec_id: str) -> str:
    """spec id 에서 가장 구체적인 도메인 키 추출."""
    if not spec_id.startswith("recipes."):
        return ""
    parts = spec_id.split(".")[1:]  # drop 'recipes'
    # try most-specific first
    for n in range(min(len(parts) - 1, 4), 0, -1):
        key = ".".join(parts[:n])
        if key in DOMAIN_LINKS:
            return key
    return ""


def extract_frontmatter(text: str) -> tuple[str, str, str]:
    if not text.startswith("---"):
        return "", "", text
    end = text.find("\n---", 3)
    if end < 0:
        return "", "", text
    return "---", text[3:end].lstrip("\n"), text[end + len("\n---") :]


def extract_linked_skills(fm: str) -> list[str]:
    match = re.search(r"^linkedSkills\s*:\s*\n((?:[ \t]+-\s*.*\n)+)", fm, re.MULTILINE)
    if not match:
        return []
    block = match.group(1)
    return [m.strip() for m in re.findall(r"-\s*(.*)", block) if m.strip()]


def upgrade_linked_skills(fm: str, spec_id: str) -> tuple[str, list[str]]:
    """linkedSkills < 3 일 때만 도메인 매핑으로 보강. 기존 항목은 유지."""
    existing = extract_linked_skills(fm)
    if len(existing) >= 3:
        return fm, []

    domain = detect_domain(spec_id)
    candidates = DOMAIN_LINKS.get(domain, [])
    if not candidates:
        return fm, []

    additions = []
    for c in candidates:
        if c not in existing and c != spec_id:
            additions.append(c)
            if len(existing) + len(additions) >= 3:
                break
    if not additions:
        return fm, []

    # 기존 block 이 있으면 끝에 추가, 없으면 새로 만들기
    match = re.search(r"^linkedSkills\s*:\s*\n((?:[ \t]+-\s*.*\n)+)", fm, re.MULTILINE)
    if match:
        block_end = match.end(1)
        new_block = "".join(f"  - {a}\n" for a in additions)
        new_fm = fm[:block_end] + new_block + fm[block_end:]
    else:
        block = "linkedSkills:\n" + "".join(f"  - {a}\n" for a in additions)
        new_fm = fm.rstrip("\n") + "\n" + block

    return new_fm, additions


def process_file(path: Path, *, dry_run: bool) -> dict:
    text = path.read_text(encoding="utf-8")
    marker, fm, body = extract_frontmatter(text)
    if not marker:
        return {"skipped": "no frontmatter"}

    id_match = re.search(r"^id\s*:\s*(.+?)\s*$", fm, re.MULTILINE)
    if not id_match:
        return {"skipped": "no id"}
    spec_id = id_match.group(1).strip().strip('"').strip("'")

    if not spec_id.startswith("recipes."):
        return {"skipped": "not recipe"}

    new_fm, additions = upgrade_linked_skills(fm, spec_id)
    if not additions:
        return {"unchanged": True}

    if not dry_run:
        new_text = marker + "\n" + new_fm.rstrip("\n") + "\n---" + body
        path.write_text(new_text, encoding="utf-8")

    return {"id": spec_id, "additions": additions}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not (args.dry_run or args.apply):
        ap.error("--dry-run 또는 --apply 명시")

    files = sorted(SPECS_ROOT.rglob("*.md"))
    total = 0
    sample = []
    for p in files:
        result = process_file(p, dry_run=args.dry_run)
        if result.get("unchanged") or result.get("skipped"):
            continue
        total += 1
        if len(sample) < 15:
            sample.append(f"  {result['id']:55s} + {result['additions']}")

    print(f"{'DRY-RUN' if args.dry_run else 'APPLIED'} — {total} recipes augmented")
    for s in sample:
        print(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())

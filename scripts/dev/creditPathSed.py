"""F1 일괄 sed — credit 평면 → 서브폴더 import 경로 갱신.

매핑:
    scoring/   metrics gradeTable creditScorecard migration calcs
    models/    chsModel merton survival excessBondPremium
    monitoring/ crisisDetector creditCycle audit history
    features/  chsFeatures sectorThresholds narrative

대상: src/dartlab/**, tests/**, scripts/**, blog/** (있으면)
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

MAPPING = {
    "metrics": "scoring",
    "gradeTable": "scoring",
    "creditScorecard": "scoring",
    "migration": "scoring",
    "calcs": "scoring",
    "chsModel": "models",
    "merton": "models",
    "survival": "models",
    "excessBondPremium": "models",
    "crisisDetector": "monitoring",
    "creditCycle": "monitoring",
    "audit": "monitoring",
    "history": "monitoring",
    "chsFeatures": "features",
    "sectorThresholds": "features",
    "narrative": "features",
}

# `dartlab.credit.<file>` → `dartlab.credit.<sub>.<file>`
PATTERN = re.compile(r"\bdartlab\.credit\.(" + "|".join(MAPPING.keys()) + r")\b")

SCAN_DIRS = ["src/dartlab", "tests", "scripts", "blog", "notebooks"]


def replaceLine(text: str) -> tuple[str, int]:
    count = 0

    def sub(m: re.Match[str]) -> str:
        nonlocal count
        count += 1
        name = m.group(1)
        return f"dartlab.credit.{MAPPING[name]}.{name}"

    return PATTERN.sub(sub, text), count


def run() -> None:
    totalFiles = 0
    totalReplacements = 0
    for d in SCAN_DIRS:
        base = ROOT / d
        if not base.exists():
            continue
        for p in base.rglob("*.py"):
            try:
                text = p.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            new, count = replaceLine(text)
            if count > 0:
                p.write_text(new, encoding="utf-8")
                totalFiles += 1
                totalReplacements += count
                print(f"  {p.relative_to(ROOT)} : {count}")
        for p in base.rglob("*.md"):
            try:
                text = p.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            new, count = replaceLine(text)
            if count > 0:
                p.write_text(new, encoding="utf-8")
                totalFiles += 1
                totalReplacements += count
                print(f"  {p.relative_to(ROOT)} : {count}")
        for p in base.rglob("*.ipynb"):
            try:
                text = p.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            new, count = replaceLine(text)
            if count > 0:
                p.write_text(new, encoding="utf-8")
                totalFiles += 1
                totalReplacements += count
                print(f"  {p.relative_to(ROOT)} : {count}")
    print(f"\n[F1-sed] {totalFiles} files, {totalReplacements} replacements.")


if __name__ == "__main__":
    run()

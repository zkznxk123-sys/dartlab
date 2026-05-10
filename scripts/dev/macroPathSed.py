"""F2 일괄 sed — macro 평면 → 서브폴더 import 경로 갱신.

매핑:
    rates/      rates yieldCurve bondRiskPremia impliedERP riskPremiums
    cycles/     cycle macroCycle regimeSwitching inflection turningPoint inventoryCycle inventory
    crisis/     crisis fci growthAtRisk rrCrisisDB
    scenarios/  scenario dalio48Match dalioCaseMatch (기존 catalog/engine/presets 보존)
    forecast/   forecast nowcast macroBacktest
    corporate/  corporate corporateAggregate
    trade/      trade termsOfTrade

대상: src/dartlab/**, tests/**, scripts/**, blog/**, notebooks/**
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

MAPPING = {
    "rates": "rates",
    "yieldCurve": "rates",
    "bondRiskPremia": "rates",
    "impliedERP": "rates",
    "riskPremiums": "rates",
    "cycle": "cycles",
    "macroCycle": "cycles",
    "regimeSwitching": "cycles",
    "inflection": "cycles",
    "turningPoint": "cycles",
    "inventoryCycle": "cycles",
    "inventory": "cycles",
    "crisis": "crisis",
    "fci": "crisis",
    "growthAtRisk": "crisis",
    "rrCrisisDB": "crisis",
    "scenario": "scenarios",
    "dalio48Match": "scenarios",
    "dalioCaseMatch": "scenarios",
    "forecast": "forecast",
    "nowcast": "forecast",
    "macroBacktest": "forecast",
    "corporate": "corporate",
    "corporateAggregate": "corporate",
    "trade": "trade",
    "termsOfTrade": "trade",
}

# `dartlab.macro.<file>` → `dartlab.macro.<sub>.<file>`
# 단어 경계 (\b) 로 부분 매치 차단. macro.scenarios. 같은 이미 sub 경로는 다시 갱신 X
PATTERN = re.compile(r"\bdartlab\.macro\.(" + "|".join(MAPPING.keys()) + r")\b(?!\.)")

SCAN_DIRS = ["src/dartlab", "tests", "scripts", "blog", "notebooks"]


def replaceLine(text: str) -> tuple[str, int]:
    count = 0

    def sub(m: re.Match[str]) -> str:
        nonlocal count
        count += 1
        name = m.group(1)
        return f"dartlab.macro.{MAPPING[name]}.{name}"

    return PATTERN.sub(sub, text), count


def run() -> None:
    totalFiles = 0
    totalReplacements = 0
    for d in SCAN_DIRS:
        base = ROOT / d
        if not base.exists():
            continue
        for ext in ("*.py", "*.md", "*.ipynb"):
            for p in base.rglob(ext):
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
    print(f"\n[F2-sed] {totalFiles} files, {totalReplacements} replacements.")


if __name__ == "__main__":
    run()

"""본문(frontmatter + 코드 제외)에 남은 약어 검증."""

from __future__ import annotations

import re
from pathlib import Path

ABBR = ["OPM", "CAPEX", "OCF", "FCF", "ICR", "DOL", "ROIC", "ROE", "GPM", "CCC", "CAGR", "DSO", "DPS", "ROA", "LCOE"]
PATTERN = re.compile(
    r"(?<![A-Za-z0-9])(" + "|".join(re.escape(a) for a in ABBR) + r")(?![A-Za-z0-9])"
)


def splitFrontmatter(text: str) -> tuple[str, str]:
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return "", text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[: i + 1]), "\n".join(lines[i + 1 :])
    return "", text


def extractBodyNonCode(body: str) -> str:
    pattern = re.compile(r"(```.*?```|`[^`\n]+`)", re.DOTALL)
    parts = pattern.split(body)
    return "".join(p for i, p in enumerate(parts) if i % 2 == 0)


def main() -> None:
    root = Path("blog")
    files = sorted(root.rglob("index.md"))
    totalHits = 0
    for fp in files:
        text = fp.read_text(encoding="utf-8")
        _, body = splitFrontmatter(text)
        pure = extractBodyNonCode(body)
        hits = PATTERN.findall(pure)
        if hits:
            counts: dict[str, int] = {}
            for h in hits:
                counts[h] = counts.get(h, 0) + 1
            diffStr = ", ".join(f"{k}={v}" for k, v in counts.items())
            print(f"BODY HITS  {fp.relative_to(root)}  [{diffStr}]")
            totalHits += sum(counts.values())
    print()
    print(f"=== body non-code 총 잔여: {totalHits}건 ===")


if __name__ == "__main__":
    main()

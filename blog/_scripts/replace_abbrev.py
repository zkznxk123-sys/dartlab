"""블로그 본문 약어 → 한국어 전수 교체.

규칙:
- frontmatter (--- ~ ---) 유지
- fenced code block (```...```) 유지
- inline code (`...`) 유지
- 나머지 본문에서 약어 → 한국어 교체
- 표 헤더/셀도 교체 (markdown 렌더러가 너비 자동 조정)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

MAPPINGS: list[tuple[str, str]] = [
    ("CAPEX", "설비투자"),
    ("ROIC", "투하자본수익률"),
    ("CAGR", "연평균성장률"),
    ("LCOE", "균등화발전비용"),
    ("OPM", "영업이익률"),
    ("OCF", "영업활동현금흐름"),
    ("FCF", "잉여현금흐름"),
    ("ICR", "이자보상배율"),
    ("DOL", "영업레버리지"),
    ("ROE", "자기자본수익률"),
    ("GPM", "매출총이익률"),
    ("CCC", "현금전환주기"),
    ("DSO", "매출채권회전일수"),
    ("DPS", "주당배당금"),
    ("ROA", "총자산수익률"),
]
MAPPINGS.sort(key=lambda x: -len(x[0]))  # 긴 패턴 먼저

ABBR_PATTERN = re.compile(r"(?<![A-Za-z0-9])(" + "|".join(re.escape(a) for a, _ in MAPPINGS) + r")(?![A-Za-z0-9])")
ABBR_MAP = dict(MAPPINGS)


def splitFrontmatter(text: str) -> tuple[str, str]:
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return "", text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            fm = "\n".join(lines[: i + 1]) + "\n"
            body = "\n".join(lines[i + 1 :])
            return fm, body
    return "", text


def replaceInText(text: str) -> str:
    return ABBR_PATTERN.sub(lambda m: ABBR_MAP[m.group(1)], text)


def replaceBody(body: str) -> str:
    # 코드블록(```...```) + 인라인 코드(`...`)는 건드리지 않음
    pattern = re.compile(r"(```.*?```|`[^`\n]+`)", re.DOTALL)
    parts = pattern.split(body)
    out: list[str] = []
    for i, part in enumerate(parts):
        if i % 2 == 0:
            out.append(replaceInText(part))
        else:
            out.append(part)
    return "".join(out)


def processFile(path: Path) -> tuple[bool, dict[str, int]]:
    text = path.read_text(encoding="utf-8")
    fm, body = splitFrontmatter(text)
    before = {abbr: len(re.findall(rf"(?<![A-Za-z0-9]){re.escape(abbr)}(?![A-Za-z0-9])", body)) for abbr, _ in MAPPINGS}
    newBody = replaceBody(body)
    result = fm + newBody
    changed = result != text
    if changed:
        path.write_text(result, encoding="utf-8")
    after = {
        abbr: len(re.findall(rf"(?<![A-Za-z0-9]){re.escape(abbr)}(?![A-Za-z0-9])", newBody)) for abbr, _ in MAPPINGS
    }
    diff = {a: before[a] - after[a] for a in before if before[a] != after[a]}
    return changed, diff


def main() -> None:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("blog")
    files = sorted(root.rglob("index.md"))
    totalChanged = 0
    totalDiff: dict[str, int] = {}
    for fp in files:
        changed, diff = processFile(fp)
        if changed:
            totalChanged += 1
            diffStr = ", ".join(f"{k}={v}" for k, v in diff.items())
            print(f"OK  {fp.relative_to(root)}  [{diffStr}]")
            for k, v in diff.items():
                totalDiff[k] = totalDiff.get(k, 0) + v
        else:
            print(f"--  {fp.relative_to(root)}")
    print()
    print(f"=== {totalChanged}/{len(files)} files changed ===")
    for k, v in sorted(totalDiff.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v} replacements")


if __name__ == "__main__":
    main()

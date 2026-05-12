"""recipe_schema_migrate — recipes/*.md frontmatter 에 gap 필드 일괄 추가.

용도
----
Recipe 6-stage lifecycle (drafted → unverified → tested → verified → curated → deprecated) 의
schema 확장 1 차. 기존 46 recipe 모두 `linkedSkills` 에서 엔진 페어를 역추론해 gap.primary 채움.
falsifier·testUniverse·expectedNovelty 는 빈 채로 두고 운영자가 후속에서 손으로 채운다.

idempotent — 이미 gap 이 있으면 스킵. 본문/다른 frontmatter 키는 손대지 않는다 (line-level
surgical insert).

실행
----
    uv run python -X utf8 scripts/dev/recipe_schema_migrate.py [--dry-run]

전제
----
- linkedSkills 가 `engines.{engine}.{name}` 형식 또는 `engines.{engine}` facade 형식.
- gap.primary = linkedSkills 안에서 빈도 1~2 위 엔진. 없으면 schema 만 빈 dict 으로.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RECIPE_DIR = REPO_ROOT / "src" / "dartlab" / "skills" / "specs" / "recipes"

_ENGINE_RE = re.compile(r"^engines\.([a-zA-Z][\w]*)")
# 분석/조합 의미가 약한 facade · meta · 인프라 엔진은 gap.primary 후보에서 제외.
# recipe = meta-카테고리, company = 단일종목 facade, mappers = 내부 정규화, dashboard/viz = 렌더링,
# data = 파이프라인. 진짜 분석 엔진끼리 페어링되지 않으면 migration skip 후 운영자 손작업 대기.
_EXCLUDED_FROM_GAP = frozenset({"recipe", "company", "mappers", "dashboard", "viz", "data"})


def _extract_linked_skills(frontmatter: str) -> list[str]:
    """frontmatter 텍스트의 linkedSkills 항목을 추출."""
    out: list[str] = []
    in_section = False
    indent: int | None = None
    for line in frontmatter.splitlines():
        if line.rstrip() == "linkedSkills:":
            in_section = True
            continue
        if not in_section:
            continue
        stripped = line.lstrip(" ")
        if not stripped:
            continue
        current_indent = len(line) - len(stripped)
        if indent is None:
            indent = current_indent
        if not stripped.startswith("- "):
            if current_indent <= 0 and ":" in stripped:
                break
            if current_indent < indent:
                break
            continue
        if current_indent < indent:
            break
        item = stripped[2:].strip()
        if not item:
            continue
        if item.startswith('"') and item.endswith('"'):
            item = item[1:-1]
        if item.startswith("'") and item.endswith("'"):
            item = item[1:-1]
        out.append(item)
    return out


def _has_top_level_key(frontmatter: str, key: str) -> bool:
    pattern = re.compile(rf"^{re.escape(key)}\s*:", re.MULTILINE)
    return bool(pattern.search(frontmatter))


def _derive_gap(linked_skills: list[str]) -> dict[str, list[str]] | None:
    counts: Counter[str] = Counter()
    for ref in linked_skills:
        match = _ENGINE_RE.match(ref)
        if not match:
            continue
        engine = match.group(1)
        if engine in _EXCLUDED_FROM_GAP:
            continue
        counts[engine] += 1
    # primary 는 ≥ 2 분석엔진. 미달이면 migration skip → 운영자가 Phase 3 에서 손작업.
    if len(counts) < 2:
        return None
    ordered = [name for name, _ in counts.most_common()]
    primary = ordered[:2]
    secondary = ordered[2:4]
    out: dict[str, list[str]] = {"primary": primary}
    if secondary:
        out["secondary"] = secondary
    return out


def _format_gap_block(gap: dict[str, list[str]]) -> str:
    lines = ["gap:"]
    for key, values in gap.items():
        lines.append(f"  {key}:")
        for value in values:
            lines.append(f"    - {value}")
    return "\n".join(lines) + "\n"


_INSERT_BEFORE_KEYS = ("source:", "lastUpdated:")


def _insert_into_frontmatter(frontmatter: str, block: str) -> str:
    """gap 블록을 source: 또는 lastUpdated: 직전에 삽입. 없으면 끝에 append."""
    lines = frontmatter.splitlines(keepends=True)
    insert_at: int | None = None
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        for key in _INSERT_BEFORE_KEYS:
            if stripped.startswith(key) and (len(line) - len(stripped)) == 0:
                insert_at = i
                break
        if insert_at is not None:
            break
    if insert_at is None:
        if not frontmatter.endswith("\n"):
            frontmatter += "\n"
        return frontmatter + block
    return "".join(lines[:insert_at]) + block + "".join(lines[insert_at:])


def migrate_file(path: Path, *, dry_run: bool = False) -> str:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return "skip:no-frontmatter"
    parts = text.split("---", 2)
    if len(parts) < 3:
        return "skip:malformed"
    frontmatter = parts[1]
    body = parts[2]

    if _has_top_level_key(frontmatter, "gap"):
        return "skip:already-has-gap"

    linked = _extract_linked_skills(frontmatter)
    gap = _derive_gap(linked)
    if not gap:
        return "skip:no-engines-derivable"

    block = _format_gap_block(gap)
    new_frontmatter = _insert_into_frontmatter(frontmatter, block)
    if new_frontmatter == frontmatter:
        return "skip:insert-noop"

    new_text = "---" + new_frontmatter + "---" + body
    if not dry_run:
        path.write_text(new_text, encoding="utf-8")
    return f"migrated:gap={gap['primary']}"


def main() -> int:
    parser = argparse.ArgumentParser(description="recipe schema migration (gap 역추론)")
    parser.add_argument("--dry-run", action="store_true", help="파일 쓰지 않고 결과만 출력")
    parser.add_argument("--path", type=Path, default=RECIPE_DIR, help="recipe 디렉터리")
    args = parser.parse_args()

    paths = sorted(args.path.rglob("*.md"))
    if not paths:
        print(f"recipe 파일 없음: {args.path}", file=sys.stderr)
        return 1

    print(f"recipe 마이그레이션 시작 — {len(paths)} 파일 (dry_run={args.dry_run})")
    summary: Counter[str] = Counter()
    for path in paths:
        result = migrate_file(path, dry_run=args.dry_run)
        head = result.split(":", 1)[0]
        summary[head] += 1
        print(f"  {path.name} — {result}")
    print()
    print("요약:")
    for kind, count in summary.most_common():
        print(f"  {kind}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

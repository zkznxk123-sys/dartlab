"""recipe sub-spec 추가 cascading CLI.

Description
-----------
recipe (재현 가능한 절차 묶음) sub-spec 추가 시 frontmatter + linkedSkills 골격
+ 6-stage lifecycle status 초기값 (`drafted`) 을 한 명령으로 생성한다.
addEngine.py · addAxis.py 의 결을 recipe 트랙에 맞춰 변형.

생성 산출물:
1. `src/dartlab/skills/specs/recipes/{name}.md` frontmatter + 6-stage status drafted

검증 자동 동행:
- `uv run python -X utf8 scripts/build/validateSkills.py {new}.md`
- (도구 폐기 — `scripts/build/generateSkills.py` 와 `src/dartlab/skills/compiler.py` 모두 삭제됨. JSON 산출물 6 종은 운영자가 직접 작성)

사용법:
    uv run python -X utf8 scripts/dev/addRecipe.py dailyMorningNote \\
        --title "매일 아침 시장 요약 recipe" \\
        --purpose "전날 마감 후 발표 공시·주가 변동을 묶어 아침 노트로 정리한다." \\
        --linked-skills engines.scan.calendar engines.gather.news engines.story.briefing

6-stage lifecycle (`drafted` → `unverified` → `tested` → `verified` → `curated` → `deprecated`)
의 상태 변경은 `scripts/dev/recipe_promote.py` 단독 권한 (feedback_recipe_lifecycle 메모리).
본 CLI 는 초기 `drafted` 만 생성.
"""

from __future__ import annotations

import argparse
import datetime
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPECS = ROOT / "src" / "dartlab" / "skills" / "specs"

RECIPE_TEMPLATE = """---
id: recipes.{name}
title: {title}
kind: curated
scope: builtin
status: drafted
category: engines
purpose: {purpose}
whenToUse:
  - {title}
  - {name}
  - recipe
linkedSkills:
{linkedSkillsBlock}
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: supported
  pyodide:
    status: supported
    notes: []
sourceRefs:
  - dartlab://skills/recipes.{name}
lastUpdated: "{today}"
---

# {title}

## 단계

1. TODO — 첫 단계 (linkedSkills 첫 항목 호출).
2. TODO — 두 번째 단계.
3. TODO — 마지막 단계.

## 입력

- TODO.

## 출력

- TODO.

## 검증

- TODO — recipe 결과의 sanity 체크 기준.

## 승급 게이트

본 recipe 는 `status: drafted` 로 시작. 다음 stage 로 승급하려면 `scripts/dev/recipe_promote.py`
단독 사용 (feedback_recipe_lifecycle 메모리 — AI / 도구 자동 변경 금지):

```bash
uv run python -X utf8 scripts/dev/recipe_promote.py recipes.{name} --to unverified
```
"""


def main() -> int:
    """recipe sub-spec 1 명령 생성 + 검증 자동 동행."""
    parser = argparse.ArgumentParser(description="recipes.{name} sub-spec 추가")
    parser.add_argument("name", help="recipe 이름 (camelCase, 예 dailyMorningNote)")
    parser.add_argument("--title", required=True, help="사람 가독 제목")
    parser.add_argument("--purpose", required=True, help="1~2 문장 목적 설명")
    parser.add_argument(
        "--linked-skills",
        nargs="*",
        default=[],
        help="recipe step 흐름의 skill id 목록 (예 engines.scan.calendar engines.gather.news)",
    )
    parser.add_argument("--dry-run", action="store_true", help="변경 없이 미리보기만")
    args = parser.parse_args()

    name = args.name
    title = args.title
    purpose = args.purpose
    linked = args.linked_skills
    today = datetime.date.today().isoformat()

    recipes_dir = SPECS / "recipes"
    if not recipes_dir.exists():
        recipes_dir.mkdir(parents=True, exist_ok=True)

    skill_md = recipes_dir / f"{name}.md"
    if skill_md.exists():
        print(f"[skip] {skill_md.relative_to(ROOT)} already exists")
        return 0

    if linked:
        linked_block = "\n".join(f"  - {item}" for item in linked)
    else:
        linked_block = "  - TODO_skill_id_1\n  - TODO_skill_id_2"

    content = RECIPE_TEMPLATE.format(
        name=name,
        title=title,
        purpose=purpose,
        linkedSkillsBlock=linked_block,
        today=today,
    )

    if args.dry_run:
        print(f"[dry-run] create {skill_md.relative_to(ROOT)}")
        return 0

    skill_md.write_text(content, encoding="utf-8")
    print(f"[create] {skill_md.relative_to(ROOT)}")

    print()
    print("[verify] validateSkills.py")
    subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(ROOT / "scripts" / "build" / "validateSkills.py"),
            str(skill_md),
        ],
        check=False,
    )
    print()
    print("[next] (도구 폐기) skills/{index,agent,...}.json 은 운영자 직접 작성")

    print()
    print("[next] 운영자 수동 작업:")
    print(f"  1. {skill_md.relative_to(ROOT)} 단계 / 입력 / 출력 / 검증 4 섹션 채우기")
    print(
        f"  2. recipe 검증 후 승급: uv run python -X utf8 scripts/dev/recipe_promote.py recipes.{name} --to unverified"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

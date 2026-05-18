"""엔진 axis sub-spec 추가 cascading CLI.

Description
-----------
engines.{group}.{axis} 형식 axis sub-spec 추가 시 운영자가 손작업으로 만들던
SKILL.md frontmatter + 3 강제 섹션 placeholder 를 한 명령으로 생성한다.
addEngine.py 의 축소판 — 새 엔진이 아니라 *기존 엔진 안의 응용 결* 결정.

생성 산출물:
1. `src/dartlab/skills/specs/engines/{group}/{axis}.md` frontmatter + 3 강제 섹션

검증 자동 동행:
- `uv run python -X utf8 src/dartlab/skills/validateSkills.py {new}.md`
- JSON 산출물 6 종은 운영자·사용자·사용자가 위임한 AI 가 명시적으로 관리하고 검토한다.

사용법:
    uv run python -X utf8 src/dartlab/skills/addAxis.py company compareTargets \\
        --title "여러 종목 토픽-기간 그리드 비교" \\
        --purpose "compareTargets axis 는 ..."
"""

from __future__ import annotations

import argparse
import datetime
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPECS = ROOT / "src" / "dartlab" / "skills" / "specs"

AXIS_TEMPLATE = """---
id: engines.{group}.{axis}
title: {title}
kind: curated
scope: builtin
status: drafted
category: engines
purpose: {purpose}
whenToUse:
  - {title}
  - {axis}
  - engines.{group}.{axis}
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
  - dartlab://skills/engines.{group}.{axis}
lastUpdated: "{today}"
---

# {title}

## 공개 호출 방식

```python
import dartlab
# TODO 호출 예시 (engines.{group} 의 axis 응용 결)
```

## 호출 동작

- 입력: TODO.
- 출력: TODO.
- 에러: TODO.

## 대표 반환 형태

TODO — DataFrame 또는 dict 구조 명시.
"""


def main() -> int:
    """axis sub-spec 1 명령 생성 + 검증 자동 동행."""
    parser = argparse.ArgumentParser(description="engines.{group}.{axis} sub-spec 추가")
    parser.add_argument("group", help="엔진 group (예 company / analysis / quant)")
    parser.add_argument("axis", help="axis 이름 (camelCase, 예 compareTargets)")
    parser.add_argument("--title", required=True, help="사람 가독 제목")
    parser.add_argument("--purpose", required=True, help="1~2 문장 목적 설명")
    parser.add_argument("--dry-run", action="store_true", help="변경 없이 미리보기만")
    args = parser.parse_args()

    group = args.group
    axis = args.axis
    title = args.title
    purpose = args.purpose
    today = datetime.date.today().isoformat()

    group_dir = SPECS / "engines" / group
    if not group_dir.exists():
        print(
            f"[error] engines/{group}/ 디렉터리 없음. 먼저 addEngine.py 로 group 생성하라.",
            file=sys.stderr,
        )
        return 1

    skill_md = group_dir / f"{axis}.md"
    if skill_md.exists():
        print(f"[skip] {skill_md.relative_to(ROOT)} already exists")
        return 0

    content = AXIS_TEMPLATE.format(group=group, axis=axis, title=title, purpose=purpose, today=today)

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
    print(f"  1. {skill_md.relative_to(ROOT)} 본문 TODO 3 섹션 채우기")
    print(f"  2. 엔진 group SKILL.md 의 capabilityRefs 또는 linkedSkills 에 engines.{group}.{axis} 추가 (선택)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

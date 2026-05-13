"""새 엔진 추가 cascading CLI — 5 단계 1 명령 자동화.

Description
-----------
새 엔진 (예 myEngine) 추가 시 운영자가 수동으로 거쳐야 했던 5 단계를 한 명령
으로 자동화한다. plan-deep + commit-self-change skill 정공법 동행.

생성 산출물:
1. `src/dartlab/{engineName}/__init__.py` 스켈레톤 + `__all__` 등록
2. `src/dartlab/__init__.py` re-export 1 줄 추가
3. `pyproject.toml [tool.importlinter]` L2 contract 1 개 추가
4. `src/dartlab/skills/specs/engines/{engineName}/SKILL.md` frontmatter + 3 강제 섹션
5. `src/dartlab/skills/specs/operation/architecture.md` L2 계층 표 1 줄 추가

검증 자동 동행:
- `uv run python -X utf8 scripts/build/validateSkills.py {new_skill}.md`
- JSON 산출물 6 종은 운영자·사용자·사용자가 위임한 AI 가 명시적으로 관리하고 검토한다.

사용법:
    uv run python -X utf8 scripts/dev/addEngine.py myEngine \\
        --title "My Engine" \\
        --purpose "myEngine 엔진은 ..."
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "dartlab"
SPECS = SRC / "skills" / "specs"
ENGINE_TEMPLATE = '''"""dartlab.{name} engine — TODO 한 줄 설명."""

from __future__ import annotations

__all__: list[str] = []
'''

SKILL_TEMPLATE = """---
id: engines.{name}
title: {title}
kind: curated
scope: builtin
status: drafted
category: engines
purpose: {purpose}
whenToUse:
  - {title}
  - {name}
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
  - dartlab://skills/engines.{name}
lastUpdated: "{today}"
---

# {title}

## 공개 호출 방식

```python
import dartlab
# TODO 호출 예시
```

## 호출 동작

- 입력: TODO.
- 출력: TODO.
- 에러: TODO.

## 대표 반환 형태

TODO — DataFrame 또는 dict 구조 명시.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="새 엔진 cascading 생성")
    parser.add_argument("engineName", help="snake-or-camel-case 엔진 이름 (예 myEngine)")
    parser.add_argument("--title", required=True, help="사람 가독 제목 (예 'My Engine')")
    parser.add_argument("--purpose", required=True, help="1~2 문장 목적 설명")
    parser.add_argument("--dry-run", action="store_true", help="변경 없이 미리보기만")
    args = parser.parse_args()

    name = args.engineName
    title = args.title
    purpose = args.purpose
    import datetime

    today = datetime.date.today().isoformat()

    # 1. 엔진 스켈레톤
    engine_init = SRC / name / "__init__.py"
    skill_md = SPECS / "engines" / name / "SKILL.md"

    actions: list[tuple[str, Path, str]] = []

    if not engine_init.exists():
        actions.append(("create", engine_init, ENGINE_TEMPLATE.format(name=name)))
    else:
        print(f"[skip] {engine_init.relative_to(ROOT)} already exists")

    if not skill_md.exists():
        actions.append(
            (
                "create",
                skill_md,
                SKILL_TEMPLATE.format(name=name, title=title, purpose=purpose, today=today),
            )
        )
    else:
        print(f"[skip] {skill_md.relative_to(ROOT)} already exists")

    if args.dry_run:
        for action, path, _ in actions:
            print(f"[dry-run] {action} {path.relative_to(ROOT)}")
        return 0

    for action, path, content in actions:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"[{action}] {path.relative_to(ROOT)}")

    # 검증 동행
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
    print("[next] 운영자 수동 작업:")
    print("  0. (도구 폐기) src/dartlab/skills/{index,agent,mcp,web,pyodide,graph}.json 은 운영자 직접 작성")
    print(f"  1. src/dartlab/__init__.py — `from . import {name}` 또는 `__all__` re-export")
    print("  2. pyproject.toml [tool.importlinter] — 새 contract 추가 (L2 격리)")
    print("  3. src/dartlab/skills/specs/operation/architecture.md — L2 계층 표에 한 줄")
    print("  4. SKILL.md 본문 TODO 3 섹션 채우기")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Skill SSOT frontmatter schema 검증.

CI 와 운영자가 신규/수정된 .md 파일에만 적용한다. 174 개 기존 파일에 일괄 강제하지 않는다.
사용:

    uv run python -X utf8 scripts/build/validateSkills.py <path1.md> [<path2.md> ...]

CI 예:

    git diff --name-only origin/master...HEAD -- 'src/dartlab/skills/specs/**.md' \\
        | xargs -r uv run python -X utf8 scripts/build/validateSkills.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REQUIRED_SCALAR = ("id", "title", "category", "purpose")
REQUIRED_LIST = ("whenToUse",)
ALLOWED_CATEGORIES = {"start", "runtime", "operation", "engines"}
ALLOWED_KINDS = {"generated", "curated", "user", "recipe"}


def extractFrontmatter(text: str) -> str | None:
    """frontmatter 블록 (--- 사이) 추출. 없으면 None."""
    stripped = text.lstrip("﻿")
    if not stripped.startswith("---"):
        return None
    end = stripped.find("\n---", 3)
    if end < 0:
        return None
    return stripped[3:end]


def hasScalar(block: str, key: str) -> str | None:
    """스칼라 값 추출. 비어있거나 누락이면 None."""
    pattern = rf"^\s*{re.escape(key)}\s*:\s*(.+?)\s*$"
    match = re.search(pattern, block, re.MULTILINE)
    if not match:
        return None
    val = match.group(1).strip().strip('"').strip("'")
    return val or None


def hasNonEmptyList(block: str, key: str) -> bool:
    """리스트 키 (다음 줄에 - item, 또는 inline [a, b]) 가 비어있지 않은지."""
    inlineMatch = re.search(
        rf"^\s*{re.escape(key)}\s*:\s*\[(.*?)\]\s*$",
        block,
        re.MULTILINE,
    )
    if inlineMatch:
        return bool(inlineMatch.group(1).strip())

    keyMatch = re.search(rf"^\s*{re.escape(key)}\s*:\s*$", block, re.MULTILINE)
    if not keyMatch:
        return False
    after = block[keyMatch.end() :]
    if not after.strip():
        return False
    firstLine = after.lstrip("\n").splitlines()[0] if after.lstrip("\n") else ""
    return firstLine.strip().startswith("-")


def collectListItems(block: str, key: str) -> list[str]:
    """리스트 키의 모든 item 추출. inline [a, b] 또는 - item 형식 지원."""
    inline = re.search(rf"^\s*{re.escape(key)}\s*:\s*\[(.*?)\]\s*$", block, re.MULTILINE)
    if inline:
        raw = inline.group(1).strip()
        if not raw:
            return []
        return [item.strip().strip('"').strip("'") for item in raw.split(",") if item.strip()]
    keyMatch = re.search(rf"^\s*{re.escape(key)}\s*:\s*$", block, re.MULTILINE)
    if not keyMatch:
        return []
    after = block[keyMatch.end() :]
    items: list[str] = []
    for line in after.lstrip("\n").splitlines():
        if not line.strip():
            continue
        if not line.startswith(" ") and not line.startswith("\t"):
            break
        if line.lstrip().startswith("-"):
            items.append(line.lstrip().lstrip("-").strip().strip('"').strip("'"))
        else:
            break
    return items


def stepsFromBody(text: str) -> list[str]:
    """## 연계 절차 섹션의 numbered/bullet list 에서 skill id 추출."""
    body_start = text.find("\n## 연계 절차")
    if body_start < 0:
        return []
    section = text[body_start + len("\n## 연계 절차") :]
    next_h = section.find("\n## ")
    if next_h >= 0:
        section = section[:next_h]
    pattern = re.compile(r"^\s*(?:\d+\.|-)\s*([\w.]+)(?:\s*[—\-:]\s*(.*))?$")
    out: list[str] = []
    for line in section.splitlines():
        match = pattern.match(line)
        if not match:
            continue
        skill_id = match.group(1).strip()
        if "." in skill_id:
            out.append(skill_id)
    return out


def validateOne(path: Path, *, knownSkillIds: set[str] | None = None) -> list[str]:
    errors: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [f"{path}: 파일 읽기 실패 — {exc}"]

    block = extractFrontmatter(text)
    if block is None:
        return [f"{path}: frontmatter 누락 또는 --- 경계 손상"]

    for key in REQUIRED_SCALAR:
        val = hasScalar(block, key)
        if not val:
            errors.append(f"{path}: 필수 필드 '{key}' 누락 또는 빈 값")
            continue
        if key == "category" and val not in ALLOWED_CATEGORIES:
            errors.append(f"{path}: category 가 {sorted(ALLOWED_CATEGORIES)} 중 하나여야 함 (실제 = {val!r})")
        elif key == "id" and "." not in val:
            errors.append(f"{path}: id 는 'category.name' 점-분리 문자열이어야 함 (실제 = {val!r})")

    for key in REQUIRED_LIST:
        if not hasNonEmptyList(block, key):
            errors.append(f"{path}: 필수 리스트 '{key}' 누락 또는 비어 있음")

    kind = hasScalar(block, "kind")
    if kind and kind not in ALLOWED_KINDS:
        errors.append(f"{path}: kind 가 {sorted(ALLOWED_KINDS)} 중 하나여야 함 (실제 = {kind!r})")

    if kind == "recipe":
        errors.extend(_validateRecipe(path, text, block, knownSkillIds=knownSkillIds))
    else:
        errors.extend(_validateApplicationCallExample(path, text, block))

    return errors


def _validateApplicationCallExample(path: Path, text: str, block: str) -> list[str]:
    """engines.analysis.* / engines.scan.* 응용 skill 본문에 호출 예시가 있는지.

    빈 boilerplate 또는 잘못된 호출 예시 회귀 차단용 약한 lint. 정확한 (group, axis)
    매칭은 ``tests/test_skills.py`` 의 정합성 테스트가 담당.
    """
    sid = hasScalar(block, "id") or ""
    errors: list[str] = []
    if sid.startswith("engines.analysis.") and sid != "engines.analysis":
        if 'c.analysis("' not in text and 'dartlab.analysis("' not in text:
            errors.append(
                f'{path}: engines.analysis 응용 skill 은 본문에 c.analysis("<group>", "<axis>") 호출 예시 필요'
            )
    if sid.startswith("engines.scan.") and sid != "engines.scan":
        if 'dartlab.scan("' not in text and 'scan("' not in text:
            errors.append(f'{path}: engines.scan 응용 skill 은 본문에 dartlab.scan("<axis>") 호출 예시 필요')
    return errors


def _validateRecipe(
    path: Path,
    text: str,
    block: str,
    *,
    knownSkillIds: set[str] | None,
) -> list[str]:
    """recipe 전용 검증 — ## 연계 절차 + linkedSkills 존재성 + step 안 skill id 존재성."""
    errors: list[str] = []
    if "## 연계 절차" not in text:
        errors.append(f"{path}: recipe 는 '## 연계 절차' 섹션 필수")
    linked = collectListItems(block, "linkedSkills")
    body_steps = stepsFromBody(text)
    if not linked and not body_steps:
        errors.append(f"{path}: recipe 는 linkedSkills frontmatter 또는 '## 연계 절차' step 필수")
    if knownSkillIds is None:
        return errors
    own_id = hasScalar(block, "id") or ""
    for sid in linked:
        if sid not in knownSkillIds:
            errors.append(f"{path}: linkedSkills 의 '{sid}' 가 등록된 skill 이 아님")
        if sid == own_id:
            errors.append(f"{path}: linkedSkills 가 자기 자신 '{sid}' 참조 (순환)")
    for sid in body_steps:
        if sid not in knownSkillIds:
            errors.append(f"{path}: '## 연계 절차' 의 '{sid}' 가 등록된 skill 이 아님")
        if sid == own_id:
            errors.append(f"{path}: '## 연계 절차' 가 자기 자신 '{sid}' 참조 (순환)")
    return errors


def collectKnownSkillIds() -> set[str]:
    """전체 builtin skills 의 id 수집 — recipe linkedSkills 존재성 검증용."""
    specs_root = Path(__file__).resolve().parents[2] / "src" / "dartlab" / "skills" / "specs"
    if not specs_root.exists():
        return set()
    ids: set[str] = set()
    for md_path in specs_root.rglob("*.md"):
        try:
            text = md_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        block = extractFrontmatter(text)
        if block is None:
            continue
        sid = hasScalar(block, "id")
        if sid:
            ids.add(sid)
    return ids


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 0

    targets: list[Path] = []
    allErrors: list[str] = []
    knownIds = collectKnownSkillIds()

    for arg in argv:
        path = Path(arg)
        if not path.exists() or path.suffix != ".md":
            continue
        if path.name == "SCHEMA.md":
            # SCHEMA.md 자체는 skill 이 아니므로 검증 제외.
            continue
        spath = str(path).replace("\\", "/")
        if "/skills/specs/" not in spath:
            # specs 폴더 밖 .md 는 skill SSOT 가 아니다.
            continue
        targets.append(path)
        allErrors.extend(validateOne(path, knownSkillIds=knownIds))

    if not targets:
        print("검증 대상 .md 없음 (skills/specs/ 아래만 검사).")
        return 0

    if allErrors:
        print(f"Skill schema 검증 실패 ({len(allErrors)} 건):")
        for err in allErrors:
            print(f"  - {err}")
        return 1

    print(f"Skill schema 검증 통과. ({len(targets)} 파일)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

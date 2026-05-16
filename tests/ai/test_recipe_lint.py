"""Recipe spec lint — recipes/*.md 가 ValidateRecipe 와 호환 가능한지 검증.

검사 항목:
1. kind == "recipe" 강제 (recipes/ 디렉터리 전체)
2. `## 공개 호출 방식` 섹션 + ```python 코드블록 ≥ 1
3. python 코드블록이 ast.parse 통과 (ValidateRecipe 가 추출해서 실행)
4. linkedSkills 가 실제 skill id 로 해상도

본 테스트는 unit marker — 데이터 로드 없음, AST/registry 만. CI Fast 안에서 실행.
실제 recipe 실행은 tests/test_recipe_validate.py (heavy + requires_data) 가 담당.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


_RECIPE_DIR = Path(__file__).resolve().parents[1] / "src" / "dartlab" / "skills" / "specs" / "recipes"


def _recipe_paths() -> list[Path]:
    # recipes/ 가 카테고리 sub-dir (macro/credit/quality/...) 으로 분리됨.
    # rglob 으로 모든 sub-dir 하위 .md 까지 수집.
    return sorted(_RECIPE_DIR.rglob("*.md"))


def _python_blocks(body: str) -> list[str]:
    """body 안의 ```python ... ``` 블록 본문을 모두 추출."""
    return re.findall(r"```python\n(.*?)```", body, flags=re.DOTALL)


def _public_call_section(body: str) -> str:
    """`## 공개 호출 방식` 섹션 본문 (다음 H2 직전까지) 추출."""
    marker = "## 공개 호출 방식"
    idx = body.find(marker)
    if idx < 0:
        return ""
    section = body[idx + len(marker) :]
    next_h2 = section.find("\n## ")
    return section if next_h2 < 0 else section[:next_h2]


def test_recipe_dir_exists():
    assert _RECIPE_DIR.is_dir(), f"recipe 디렉터리 없음: {_RECIPE_DIR}"
    paths = _recipe_paths()
    assert len(paths) >= 40, f"recipe 수 비정상: {len(paths)}"


def test_every_recipe_has_kind_recipe():
    from dartlab.skills.registry import _readMarkdownSkill

    failures: list[str] = []
    for path in _recipe_paths():
        text = path.read_text(encoding="utf-8")
        data = _readMarkdownSkill(text, path)
        if data.get("kind") != "recipe":
            failures.append(f"{path.name}: kind={data.get('kind')!r}")
    assert not failures, "recipes/ 의 spec 은 kind: recipe 강제\n" + "\n".join(failures)


def test_every_recipe_public_call_block_parses_as_python():
    """ValidateRecipe 가 추출해서 실행할 코드블록이 AST 단계에서 깨지면 안 된다."""
    from dartlab.skills.registry import _readMarkdownSkill

    failures: list[str] = []
    for path in _recipe_paths():
        text = path.read_text(encoding="utf-8")
        data = _readMarkdownSkill(text, path)
        body = str((data.get("source") or {}).get("body") or "")
        section = _public_call_section(body)
        if not section.strip():
            failures.append(f"{path.name}: '## 공개 호출 방식' 섹션 누락")
            continue
        blocks = _python_blocks(section)
        if not blocks:
            failures.append(f"{path.name}: '## 공개 호출 방식' 안에 python 코드블록 없음")
            continue
        for idx, code in enumerate(blocks):
            try:
                ast.parse(code)
            except SyntaxError as exc:
                failures.append(f"{path.name} block#{idx}: SyntaxError {exc.msg} (line {exc.lineno})")
    assert not failures, "recipe '## 공개 호출 방식' 코드블록 파싱 실패:\n" + "\n".join(failures)


def test_recipe_linked_skills_resolve_to_known_ids():
    """linkedSkills 의 모든 ref 가 실제 skill 로 해상도. 자기참조·미존재 detect."""
    from dartlab.skills import listSkills

    all_ids = {spec.id for spec in listSkills()}
    failures: list[str] = []
    for spec in listSkills():
        if spec.kind != "recipe":
            continue
        for linked in spec.linkedSkills:
            if linked == spec.id:
                failures.append(f"{spec.id}: 자기참조 ({linked})")
                continue
            # 정확 일치 또는 prefix (engines.credit 류 facade) 양쪽 허용.
            if linked in all_ids:
                continue
            if any(known.startswith(linked + ".") for known in all_ids):
                continue
            # facade-only id (engines.credit 등) 도 listSkills 가 노출하면 OK.
            failures.append(f"{spec.id}: linkedSkills 미해상도 → {linked}")
    assert not failures, "recipe linkedSkills 해상도 실패:\n" + "\n".join(failures)


def test_recipe_gap_when_present_has_primary_pair():
    """gap 필드가 frontmatter 에 있으면 primary 는 ≥2 엔진. 첫 wave 는 존재 강제 X (warn 만)."""
    from dartlab.skills import listSkills

    failures: list[str] = []
    for spec in listSkills():
        if spec.kind != "recipe":
            continue
        if not spec.gap:
            continue
        primary = spec.gap.get("primary")
        if not isinstance(primary, list) or len(primary) < 2:
            failures.append(f"{spec.id}: gap.primary must be list of ≥2 engine names (got {primary!r})")
    assert not failures, "recipe gap 구조 위반:\n" + "\n".join(failures)


def test_recipe_falsifier_when_present_has_description():
    from dartlab.skills import listSkills

    failures: list[str] = []
    for spec in listSkills():
        if spec.kind != "recipe":
            continue
        if not spec.falsifier:
            continue
        desc = spec.falsifier.get("description")
        if not isinstance(desc, str) or not desc.strip():
            failures.append(f"{spec.id}: falsifier.description must be non-empty string")
    assert not failures, "recipe falsifier 구조 위반:\n" + "\n".join(failures)

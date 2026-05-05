"""회귀 가드 — ai/ 코드가 기존 curated/observed/auditP/official spec 을 수정하지 않는다.

proposeSkill 만 새 파일 생성 가능. 기존 파일 덮어쓰기는 _spec_exists 체크로 차단.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_AI_ROOT = Path(__file__).resolve().parents[2] / "src" / "dartlab" / "ai"


@pytest.mark.unit
def test_proposeSkill_blocks_overwriting_existing_spec(monkeypatch, tmp_path) -> None:
    from dartlab.ai.tools import proposeSkill as module
    from dartlab.ai.tools.proposeSkill import proposeSkill

    fake = tmp_path / "specs"
    monkeypatch.setattr(module, "_SPEC_ROOT", fake)

    target_dir = fake / "engines" / "company"
    target_dir.mkdir(parents=True)
    target = target_dir / "existing.md"
    target.write_text(
        "---\nid: engines.company.existing\nkind: curated\nstatus: official\n---\n원본",
        encoding="utf-8",
    )

    result = proposeSkill(
        skillId="engines.company.existing",
        title="hijack 시도",
        purpose="기존 spec 수정 시도",
        body="oops",
    )
    assert result.ok is False
    assert result.error == "spec_exists"
    # 원본 보존
    text = target.read_text(encoding="utf-8")
    assert "원본" in text
    assert "oops" not in text


@pytest.mark.unit
def test_no_ai_module_writes_to_skills_specs_path() -> None:
    """ai/ 안의 어떤 파일도 skills/specs 경로를 직접 write 하지 않는다 (proposeSkill 제외)."""
    violations: list[str] = []
    for path in _AI_ROOT.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(_AI_ROOT.parent).as_posix()
        if rel.endswith("/proposeSkill.py"):
            continue  # 유일하게 spec 작성 허용

        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue

        # skills/specs write 의심 패턴 — write_text + skills/specs 동시 출현
        if "skills/specs" in text or "skills\\specs" in text:
            if "write_text" in text or "open(" in text:
                violations.append(rel)

    assert not violations, "skills/specs write 의심:\n" + "\n".join(violations)

"""회귀 가드 — proposeSkill 작성 spec 의 frontmatter 가 SkillSpec schema 통과."""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_propose_skill_writes_valid_frontmatter(monkeypatch, tmp_path) -> None:
    from dartlab.ai.tools import proposeSkill as proposeSkill_module
    from dartlab.ai.tools.proposeSkill import proposeSkill

    # spec root 를 tmp 로 redirect
    fake_skills = tmp_path / "skills"
    fake_specs = fake_skills / "specs"
    monkeypatch.setattr(proposeSkill_module, "_SPEC_ROOT", fake_specs)

    result = proposeSkill(
        skillId="engines.scan.testRapid",
        title="테스트 스캔",
        purpose="회귀 가드용 테스트 skill",
        category="engines",
        whenToUse=["테스트 시"],
        capabilityRefs=["scan.test"],
        requiredEvidence=["target", "metric"],
        body="본문\n",
    )
    assert result.ok is True
    target = fake_specs / "engines" / "scan" / "testRapid.md"
    assert target.exists()
    text = target.read_text(encoding="utf-8")
    assert "id: engines.scan.testRapid" in text
    assert "kind: generated" in text
    assert "status: unverified" in text
    assert "본문" in text


@pytest.mark.unit
def test_propose_skill_rejects_invalid_id() -> None:
    from dartlab.ai.tools.proposeSkill import proposeSkill

    result = proposeSkill(skillId="bad.id", title="x", purpose="y")
    assert result.ok is False
    assert result.error == "invalid_id_shape"


@pytest.mark.unit
def test_propose_skill_does_not_overwrite_existing(monkeypatch, tmp_path) -> None:
    from dartlab.ai.tools import proposeSkill as proposeSkill_module
    from dartlab.ai.tools.proposeSkill import proposeSkill

    fake_specs = tmp_path / "specs"
    monkeypatch.setattr(proposeSkill_module, "_SPEC_ROOT", fake_specs)

    r1 = proposeSkill(skillId="engines.macro.first", title="A", purpose="A", body="first")
    assert r1.ok is True

    r2 = proposeSkill(skillId="engines.macro.first", title="B", purpose="B", body="second")
    assert r2.ok is False
    assert r2.error == "spec_exists"

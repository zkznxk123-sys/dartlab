"""P1 6 종 도구 — readSkill / readCapability / saveArtifact / proposeSkill 단위.

5 패스 작업대 (P1.B) 가 들어오기 전에 도구 자체 계약을 검증한다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

from dartlab.ai.tools.proposeSkill import proposeSkill
from dartlab.ai.tools.readCapability import readCapability
from dartlab.ai.tools.readSkill import readSkill
from dartlab.ai.tools.registry import WORKBENCH_TOOLS, executeTool, listToolNames
from dartlab.ai.tools.saveArtifact import saveArtifact

# ── readSkill ────────────────────────────────────────────────────────────────


def test_read_skill_search_returns_skill_refs():
    result = readSkill(query="수익성 분석", limit=5)
    assert result.ok is True
    assert all(ref.kind == "skillRef" for ref in result.refs)
    assert all("score" in ref.payload for ref in result.refs)


def test_read_skill_with_explicit_id_returns_full_body():
    search = readSkill(query="수익성", limit=1)
    if not search.refs:
        pytest.skip("skill 인덱스가 비어 있어 본 케이스를 검증할 수 없다")
    skill_id = search.refs[0].payload["id"]
    result = readSkill(skillId=skill_id)
    assert result.ok is True
    assert len(result.refs) == 1
    assert result.refs[0].payload["id"] == skill_id
    assert "body" in result.refs[0].payload


def test_read_skill_requires_query_or_id():
    result = readSkill()
    assert result.ok is False
    assert result.error == "missing_args"


# ── readCapability ───────────────────────────────────────────────────────────


def test_read_capability_by_name_returns_docstring():
    result = readCapability(name="dartlab")
    assert result.ok is True
    assert result.refs[0].kind == "capabilityRef"
    assert "docstring" in result.data


def test_read_capability_unknown_name_fails_softly():
    result = readCapability(name="totally.fake.module.path")
    assert result.ok is False
    assert result.error == "capability_not_found"


def test_read_capability_requires_args():
    assert readCapability().ok is False


# ── saveArtifact ─────────────────────────────────────────────────────────────


def test_save_artifact_writes_file_and_returns_ref(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "dartlab.ai.tools.saveArtifact._ARTIFACT_ROOT",
        tmp_path / "ask_artifacts",
    )
    result = saveArtifact("test.txt", "hello", kind="note")
    assert result.ok is True
    artifact = tmp_path / "ask_artifacts" / "test.txt"
    assert artifact.read_text(encoding="utf-8") == "hello"
    assert result.refs[0].kind == "artifactRef"


def test_save_artifact_rejects_blank_name():
    result = saveArtifact("", "x")
    assert result.ok is False


# ── proposeSkill ─────────────────────────────────────────────────────────────


def test_propose_skill_writes_generated_spec_with_unverified_status(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "dartlab.ai.tools.proposeSkill._SKILLS_ROOT",
        tmp_path / "specs",
    )
    result = proposeSkill(
        id="generated.test.checkProfit",
        title="이익 점검 (테스트)",
        purpose="테스트용 자동 생성 spec",
        whenToUse=["테스트 케이스 동안만"],
        capabilityRefs=["Company.show"],
        requiredEvidence=["target", "value"],
        body="절차: 1. show 호출. 2. 영업이익률 계산.",
    )
    assert result.ok is True
    written = tmp_path / "specs" / "engines" / "generated" / "checkProfit.md"
    text = written.read_text(encoding="utf-8")
    assert "kind: generated" in text
    assert "status: unverified" in text
    assert "id: generated.test.checkProfit" in text
    assert "절차: 1. show" in text


def test_propose_skill_refuses_overwrite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "dartlab.ai.tools.proposeSkill._SKILLS_ROOT",
        tmp_path / "specs",
    )
    proposeSkill(id="generated.dup", title="중복 테스트")
    again = proposeSkill(id="generated.dup", title="중복 테스트 2")
    assert again.ok is False
    assert again.error == "skill_already_exists"


# ── registry 통합 ────────────────────────────────────────────────────────────


def test_workbench_tools_all_registered():
    names = set(listToolNames())
    for tool in WORKBENCH_TOOLS:
        assert tool in names, f"{tool} 가 registry 에 없다"


def test_execute_tool_dispatches_read_skill():
    result = executeTool("read_skill", {"query": "수익성", "limit": 3})
    assert result["ok"] is True or result["error"] is None or result["error"] == "skill_not_found"


def test_execute_tool_dispatches_save_artifact(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "dartlab.ai.tools.saveArtifact._ARTIFACT_ROOT",
        tmp_path / "ask_artifacts",
    )
    result = executeTool("save_artifact", {"name": "via_registry.txt", "content": "ok"})
    assert result["ok"] is True
    assert (tmp_path / "ask_artifacts" / "via_registry.txt").exists()

"""feedback_*.md 합성기 read-only 회귀 가드."""

from __future__ import annotations

from pathlib import Path

import pytest


def _writeMemory(path: Path, *, name: str, mtype: str, description: str, body: str) -> None:
    frontmatter = f"---\nname: {name}\ndescription: {description}\nmetadata:\n  type: {mtype}\n---\n\n{body}\n"
    path.write_text(frontmatter, encoding="utf-8")


@pytest.fixture
def fake_memory_dir(tmp_path):
    """3 개 가짜 feedback 메모리 + 1 개 비-feedback 파일."""
    _writeMemory(
        tmp_path / "feedback_alpha.md",
        name="feedback-alpha",
        mtype="feedback",
        description="삼성전자 매핑 자동화 금지 — 운영자 명시 트리거",
        body="자동 sweep 회귀 차단. 관련: [[feedback_beta]] [[feedback_gamma]]\n매퍼 cycle 17 사례.",
    )
    _writeMemory(
        tmp_path / "feedback_beta.md",
        name="feedback-beta",
        mtype="feedback",
        description="docstring 자동 도구 금지 — 깊이 0 회귀",
        body="autoFillNine 894 stub 도배 사례. 관련: [[feedback_alpha]]",
    )
    _writeMemory(
        tmp_path / "feedback_gamma.md",
        name="feedback-gamma",
        mtype="project",
        description="recipe lifecycle 6-stage",
        body="drafted unverified tested verified curated deprecated 6 단계.",
    )
    # 비-feedback 파일은 무시
    (tmp_path / "MEMORY.md").write_text("# index\n", encoding="utf-8")
    return tmp_path


@pytest.mark.unit
def test_synth_counts_files_and_chars(fake_memory_dir):
    from dartlab.ai.memory.synthesizer import synthFeedbackStats

    stats = synthFeedbackStats(fake_memory_dir, writeReport=False)
    assert stats.file_count == 3
    assert stats.total_chars > 0
    assert stats.avg_chars > 0


@pytest.mark.unit
def test_synth_type_distribution(fake_memory_dir):
    from dartlab.ai.memory.synthesizer import synthFeedbackStats

    stats = synthFeedbackStats(fake_memory_dir, writeReport=False)
    assert stats.type_distribution.get("feedback") == 2
    assert stats.type_distribution.get("project") == 1


@pytest.mark.unit
def test_synth_link_in_degree_normalizes_dash_to_underscore(fake_memory_dir):
    from dartlab.ai.memory.synthesizer import synthFeedbackStats

    stats = synthFeedbackStats(fake_memory_dir, writeReport=False)
    link_dict = dict(stats.link_in_degree)
    assert link_dict.get("feedback_alpha") == 1
    assert link_dict.get("feedback_beta") == 1
    assert link_dict.get("feedback_gamma") == 1


@pytest.mark.unit
def test_synth_ko_tokens_weighted_by_description(fake_memory_dir):
    from dartlab.ai.memory.synthesizer import synthFeedbackStats

    stats = synthFeedbackStats(fake_memory_dir, writeReport=False)
    ko_dict = dict(stats.ko_top_tokens)
    # description "삼성전자 매핑 자동화 금지" 가 2× 가중 → "삼성전자", "매핑" 토큰 존재
    assert "삼성전자" in ko_dict
    assert ko_dict["삼성전자"] >= 2


@pytest.mark.unit
def test_synth_writes_report_to_synth_dir(fake_memory_dir):
    from dartlab.ai.memory.synthesizer import synthFeedbackStats

    stats = synthFeedbackStats(fake_memory_dir, writeReport=True)
    output = fake_memory_dir / "_synth" / "feedbackStats.md"
    assert output.exists()
    text = output.read_text(encoding="utf-8")
    assert "# feedback_*.md 통계 합성" in text
    assert "read-only" in text
    assert str(stats.file_count) in text


@pytest.mark.unit
def test_synth_does_not_modify_original_feedback_files(fake_memory_dir):
    from dartlab.ai.memory.synthesizer import synthFeedbackStats

    before = {p.name: p.read_text(encoding="utf-8") for p in fake_memory_dir.glob("feedback_*.md")}
    synthFeedbackStats(fake_memory_dir, writeReport=True)
    after = {p.name: p.read_text(encoding="utf-8") for p in fake_memory_dir.glob("feedback_*.md")}
    assert before == after, "원본 feedback_*.md 가 수정됨 — read-only 위반"


@pytest.mark.unit
def test_synth_handles_invalid_frontmatter_gracefully(tmp_path):
    from dartlab.ai.memory.synthesizer import synthFeedbackStats

    (tmp_path / "feedback_bad.md").write_text("no frontmatter here", encoding="utf-8")
    (tmp_path / "feedback_yaml_broken.md").write_text("---\n:\n---\nbody\n", encoding="utf-8")
    _writeMemory(
        tmp_path / "feedback_ok.md",
        name="ok",
        mtype="feedback",
        description="ok",
        body="body",
    )
    stats = synthFeedbackStats(tmp_path, writeReport=False)
    assert stats.file_count == 1, "유효 frontmatter 1 건만 카운트"


@pytest.mark.unit
def test_synth_empty_dir(tmp_path):
    from dartlab.ai.memory.synthesizer import synthFeedbackStats

    stats = synthFeedbackStats(tmp_path, writeReport=False)
    assert stats.file_count == 0
    assert stats.total_chars == 0
    assert stats.avg_chars == 0.0

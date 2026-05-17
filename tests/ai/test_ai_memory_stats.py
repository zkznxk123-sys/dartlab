"""memory/stats.py — skill 사용 통계 + status 승격 후보 단위 검증."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def stats_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "skill_stats.json"
    monkeypatch.setenv("DARTLAB_SKILL_STATS_PATH", str(path))
    return path


def test_record_skill_usage_persists_to_path(stats_path: Path):
    from dartlab.ai.memory import loadStats, recordSkillUsage

    entry = recordSkillUsage("engines.test.alpha", success=True, valueRefs=3)
    assert entry.usageCount == 1
    assert entry.successCount == 1
    assert entry.valueRefCount == 3
    assert stats_path.exists()

    again = loadStats()
    assert "engines.test.alpha" in again
    assert again["engines.test.alpha"].lastUsedTs


def test_record_skill_usage_accumulates(stats_path: Path):
    from dartlab.ai.memory import loadStats, recordSkillUsage

    recordSkillUsage("engines.test.beta", success=True, valueRefs=2)
    recordSkillUsage("engines.test.beta", success=False, valueRefs=1)
    recordSkillUsage("engines.test.beta", success=True, valueRefs=4)

    entry = loadStats()["engines.test.beta"]
    assert entry.usageCount == 3
    assert entry.successCount == 2
    assert entry.valueRefCount == 7
    assert pytest.approx(entry.successRate, abs=1e-6) == 2 / 3
    assert pytest.approx(entry.avgValueRefs, abs=1e-6) == 7 / 3


def test_promotion_candidates_lifts_unverified_to_observed(stats_path: Path, monkeypatch: pytest.MonkeyPatch):
    """unverified spec 가 사용 ≥5 + 성공률 ≥0.7 면 observed 후보로 잡힌다."""

    from dartlab.ai.memory import promotionCandidates, recordSkillUsage

    # Fake getSkill 반환값을 만든다 — 실 spec 파일을 건드리지 않는다.
    class _FakeSpec:
        status = "unverified"

    monkeypatch.setattr("dartlab.skills.getSkill", lambda skillId, includeUser=True: _FakeSpec())

    for _ in range(5):
        recordSkillUsage("engines.test.gamma", success=True, valueRefs=1)
    for _ in range(2):
        recordSkillUsage("engines.test.gamma", success=False, valueRefs=0)

    candidates = promotionCandidates()
    target = next((c for c in candidates if c["skillId"] == "engines.test.gamma"), None)
    assert target is not None
    assert target["fromStatus"] == "unverified"
    assert target["toStatus"] == "observed"


def test_promotion_candidates_skip_low_usage(stats_path: Path, monkeypatch: pytest.MonkeyPatch):
    from dartlab.ai.memory import promotionCandidates, recordSkillUsage

    class _FakeSpec:
        status = "unverified"

    monkeypatch.setattr("dartlab.skills.getSkill", lambda skillId, includeUser=True: _FakeSpec())

    recordSkillUsage("engines.test.delta", success=True, valueRefs=1)
    recordSkillUsage("engines.test.delta", success=True, valueRefs=1)

    candidates = promotionCandidates()
    target = next((c for c in candidates if c["skillId"] == "engines.test.delta"), None)
    assert target is None

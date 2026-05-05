"""P4 — Status 자동 승격 시그널 + 운영자 confirm 게이트."""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_unverified_to_observed_requires_confirm(monkeypatch, tmp_path) -> None:
    from dartlab.ai.memory import promotion, stats

    fake = tmp_path / "skill_stats.jsonl"
    monkeypatch.setattr(stats, "_STATS_PATH", fake)

    for _ in range(6):
        stats.recordOutcome("engines.scan.testing", ok=True, valueRefs=2)

    candidates = promotion.promotionCandidates({"engines.scan.testing": "unverified"})
    assert len(candidates) == 1
    cand = candidates[0]
    assert cand.fromStatus == "unverified"
    assert cand.toStatus == "observed"
    assert cand.requiresConfirm is True


@pytest.mark.unit
def test_below_threshold_no_candidate(monkeypatch, tmp_path) -> None:
    from dartlab.ai.memory import promotion, stats

    fake = tmp_path / "skill_stats.jsonl"
    monkeypatch.setattr(stats, "_STATS_PATH", fake)

    for _ in range(3):
        stats.recordOutcome("engines.scan.young", ok=True, valueRefs=1)

    candidates = promotion.promotionCandidates({"engines.scan.young": "unverified"})
    assert candidates == []


@pytest.mark.unit
def test_observed_to_auditP_auto(monkeypatch, tmp_path) -> None:
    from dartlab.ai.memory import promotion, stats

    fake = tmp_path / "skill_stats.jsonl"
    monkeypatch.setattr(stats, "_STATS_PATH", fake)

    for _ in range(20):
        stats.recordOutcome("engines.scan.mature", ok=True, valueRefs=2)

    candidates = promotion.promotionCandidates({"engines.scan.mature": "observed"})
    assert len(candidates) == 1
    cand = candidates[0]
    assert cand.fromStatus == "observed"
    assert cand.toStatus == "auditP"
    assert cand.requiresConfirm is False


@pytest.mark.unit
def test_low_success_rate_blocks_observed_promotion(monkeypatch, tmp_path) -> None:
    from dartlab.ai.memory import promotion, stats

    fake = tmp_path / "skill_stats.jsonl"
    monkeypatch.setattr(stats, "_STATS_PATH", fake)

    for _ in range(10):
        stats.recordOutcome("engines.scan.flaky", ok=False, valueRefs=0)
    for _ in range(2):
        stats.recordOutcome("engines.scan.flaky", ok=True, valueRefs=1)

    candidates = promotion.promotionCandidates({"engines.scan.flaky": "unverified"})
    assert candidates == []

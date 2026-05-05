"""P5 — recall/remember + lens 패널."""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_remember_then_recall_finds_match(monkeypatch, tmp_path) -> None:
    from dartlab.ai.memory import decisions

    fake = tmp_path / "decisions.jsonl"
    monkeypatch.setattr(decisions, "_DECISIONS_PATH", fake)

    decisions.remember("삼성전자 2024 영업이익 분석은 PER 12 가 적절", tags=["valuation"])
    decisions.remember("BYD 와 테슬라 영업효율 비교는 마진 기준", tags=["compare"])

    hits = decisions.recall("삼성전자 PER", k=3)
    assert any("삼성전자" in h.get("text", "") for h in hits)


@pytest.mark.unit
def test_recall_returns_empty_for_no_overlap(monkeypatch, tmp_path) -> None:
    from dartlab.ai.memory import decisions

    fake = tmp_path / "decisions.jsonl"
    monkeypatch.setattr(decisions, "_DECISIONS_PATH", fake)

    decisions.remember("재무제표 분석 노트")
    hits = decisions.recall("zzzzzz nothing", k=5)
    assert hits == []


@pytest.mark.unit
def test_lenses_module_exposes_four_lenses() -> None:
    from dartlab.ai.lenses import LENSES

    assert set(LENSES.keys()) == {"fundamental", "macro", "technical", "sentiment"}
    for prompt in LENSES.values():
        assert "관점:" in prompt


@pytest.mark.unit
def test_lens_prompts_distinct() -> None:
    from dartlab.ai.lenses import LENSES

    prompts = list(LENSES.values())
    assert len(set(prompts)) == 4

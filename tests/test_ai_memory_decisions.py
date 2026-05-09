"""decisions memory — recall / remember 단위."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def decisions_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "decisions.jsonl"
    monkeypatch.setenv("DARTLAB_DECISIONS_PATH", str(path))
    return path


def test_remember_then_recall_returns_top_match(decisions_path: Path):
    from dartlab.ai.memory import DecisionMemo, recall, remember

    remember(DecisionMemo(question="삼성전자 ROE", answer="ROE 12.3%", refs=["valueRef:roe"]))
    remember(DecisionMemo(question="LG전자 OPM", answer="OPM 5.1%", refs=["valueRef:opm"]))
    remember(DecisionMemo(question="현대차 부채비율", answer="113%", refs=["valueRef:debt"]))

    matches = recall("삼성전자 ROE 추세", k=2)
    assert matches
    assert matches[0].question == "삼성전자 ROE"


def test_recall_returns_empty_for_unrelated_question(decisions_path: Path):
    from dartlab.ai.memory import DecisionMemo, recall, remember

    remember(DecisionMemo(question="삼성전자 ROE", answer="x"))
    matches = recall("매크로 사이클 어디쯤", k=3)
    assert matches == []


def test_recall_handles_missing_file(decisions_path: Path):
    from dartlab.ai.memory import recall

    assert recall("아무 질문") == []
